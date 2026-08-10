from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from hashlib import sha256
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import and_, or_, select, text
from sqlalchemy.orm import Session, selectinload

from app.assistant_chat import governed_chat
from app.assistant_tools import ToolInputError, invoke_tool
from app.chat_limiter import ChatLimiter
from app.config import Settings
from app.database import build_engine, build_session_factory, create_schema, session_dependency
from app.models import Asset, Finding, Incident, IncidentFinding, Observation
from app.platform import (
    asset_response,
    create_quality_finding,
    decode_cursor,
    detect_multi_source_freshness,
    detect_telemetry_anomaly,
    encode_cursor,
    ensure_asset,
    evaluate_quality,
    finding_response,
    incident_detail_response,
    incident_response,
    observation_response,
    transition_incident,
    utc_now,
)
from app.read_models import linked_observation_ids, operations_briefing_response
from app.schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantToolRequest,
    AssistantToolResponse,
    ErrorResponse,
    IncidentDetailResponse,
    IncidentTransitionRequest,
    ListResponse,
    ObservationBatchRequest,
    ObservationBatchResponse,
    ObservationResponse,
    OperationsBriefingResponse,
)


def error_payload(
    request: Request, code: str, message: str, details: list[dict] | None = None
) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": getattr(request.state, "request_id", "unknown"),
        }
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings.from_environment()
    engine = build_engine(app_settings.database_url)
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if app_settings.auto_create_schema:
            create_schema(engine)
        yield
        engine.dispose()

    app = FastAPI(title="Sonoran Operations Intelligence API", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.settings = app_settings
    app.state.chat_limiter = ChatLimiter()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "request could not be completed"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(request, "request_error", detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"path": ".".join(map(str, error["loc"])), "reason": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_payload(
                request, "validation_error", "One or more values are invalid.", details
            ),
        )

    def get_session() -> Session:
        yield from session_dependency(session_factory)

    @app.post(
        "/api/v1/assistant/tools/{tool_name}",
        response_model=AssistantToolResponse,
        responses={422: {"model": ErrorResponse}},
    )
    def invoke_assistant_evidence_tool(
        tool_name: str,
        request: AssistantToolRequest,
        session: Session = Depends(get_session),
    ) -> AssistantToolResponse:
        """Deterministic, read-only evidence mode for the synthetic demo; no LLM is called."""
        try:
            result = invoke_tool(
                session,
                tool_name,
                {**request.arguments, "site_id": request.site_id},
            )
        except ToolInputError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return AssistantToolResponse(
            mode="deterministic_evidence_tool",
            tool_name=tool_name,
            site_id=request.site_id,
            **result.as_dict(),
        )

    @app.post(
        "/api/v1/assistant/chat",
        response_model=AssistantChatResponse,
        responses={503: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    def assistant_chat(
        request: AssistantChatRequest, raw_request: Request, session: Session = Depends(get_session)
    ) -> AssistantChatResponse:
        """LLM wording over bounded, cited read-only evidence tools; no operational authority."""
        if not app_settings.openai_api_key:
            raise HTTPException(
                status_code=503, detail="Evidence chat is not configured for this deployment."
            )
        raw_client = raw_request.headers.get(
            "X-Forwarded-For", raw_request.client.host if raw_request.client else "unknown"
        ).split(",")[0].strip()
        safety_identifier = sha256(
            f"{app_settings.chat_safety_salt}:{raw_client}".encode()
        ).hexdigest()
        if app.state.chat_limiter.acquire(raw_client) is None:
            raise HTTPException(
                status_code=429, detail="Chat is temporarily rate limited. Please try later."
            )
        try:
            from openai import OpenAI

            result = governed_chat(
                OpenAI(api_key=app_settings.openai_api_key),
                app_settings.openai_model,
                session,
                request.site_id,
                [{"role": item.role, "content": item.content} for item in request.messages],
                safety_identifier,
            )
        except Exception as error:
            raise HTTPException(
                status_code=503, detail="Evidence chat is temporarily unavailable."
            ) from error
        finally:
            app.state.chat_limiter.release()
        return AssistantChatResponse(mode="governed_evidence_chat", **result)

    @app.get("/api/v1/health")
    def health(session: Session = Depends(get_session)) -> dict[str, str]:
        session.execute(text("SELECT 1"))
        return {"status": "ok", "service": "sonoran-ops-api"}

    @app.post(
        "/api/v1/ingestion/observations",
        response_model=ObservationBatchResponse,
        status_code=201,
        responses={422: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    )
    def ingest_observations(
        batch: ObservationBatchRequest,
        idempotency_header: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
        session: Session = Depends(get_session),
    ) -> ObservationBatchResponse:
        # The batch key gives transport retries an explicit contract. Per-observation keys
        # enforce persistence idempotency so a partially retried batch remains safe.
        del idempotency_header
        accepted: list[ObservationResponse] = []
        duplicate_count = 0
        flagged_count = 0
        last_new_observation: Observation | None = None
        now = utc_now()
        with session.begin():
            for input_observation in batch.observations:
                existing = session.scalar(
                    select(Observation)
                    .options(selectinload(Observation.asset))
                    .where(Observation.idempotency_key == input_observation.idempotency_key)
                )
                if existing is not None:
                    duplicate_count += 1
                    flags = list(existing.quality_flags)
                    if "duplicate" not in flags:
                        flags.append("duplicate")
                        existing.quality_flags = flags
                        existing.quality_status = "accepted_with_flags"
                        create_quality_finding(session, existing, ["duplicate"], now)
                    accepted.append(observation_response(existing))
                    continue

                ensure_asset(session, input_observation.asset_ref)
                flags = evaluate_quality(session, input_observation, batch.source.source_id, now)
                observation = Observation(
                    observation_id=f"obs_{uuid4().hex}",
                    idempotency_key=input_observation.idempotency_key,
                    source_id=batch.source.source_id,
                    source_type=batch.source.source_type,
                    received_via=batch.source.received_via,
                    asset_id=input_observation.asset_ref.asset_id,
                    kind=input_observation.kind,
                    metric=input_observation.metric,
                    value=input_observation.value,
                    unit=input_observation.unit,
                    record_type=input_observation.record_type,
                    attributes=input_observation.attributes,
                    observed_at=input_observation.observed_at,
                    source_recorded_at=input_observation.source_recorded_at,
                    ingested_at=now,
                    quality_status="accepted_with_flags" if flags else "accepted",
                    quality_flags=flags,
                )
                session.add(observation)
                session.flush()
                if flags:
                    flagged_count += 1
                    create_quality_finding(session, observation, flags, now)
                # The detector itself admits only clean records or timing/order-degraded
                # records; all other flagged data remains excluded from its evidence.
                detect_telemetry_anomaly(session, observation, now)
                session.flush()
                last_new_observation = observation
                accepted.append(observation_response(observation))
            if last_new_observation is not None:
                detect_multi_source_freshness(session, last_new_observation, now)
        return ObservationBatchResponse(
            accepted_count=len(batch.observations) - duplicate_count,
            duplicate_count=duplicate_count,
            flagged_count=flagged_count,
            observations=accepted,
        )

    @app.get("/api/v1/assets", response_model=ListResponse)
    def list_assets(
        session: Session = Depends(get_session),
        limit: int = Query(default=50, ge=1, le=200),
        site_id: str | None = None,
        cursor: str | None = None,
    ) -> ListResponse:
        statement = select(Asset).order_by(Asset.asset_id)
        if site_id:
            statement = statement.where(Asset.site_id == site_id)
        if cursor:
            values = decode_cursor(cursor)
            asset_id = values.get("asset_id")
            if asset_id is None:
                raise HTTPException(status_code=422, detail="asset cursor is invalid")
            statement = statement.where(Asset.asset_id > asset_id)
        assets = list(session.scalars(statement.limit(limit + 1)))
        next_cursor = None
        if len(assets) > limit:
            last = assets[limit - 1]
            next_cursor = encode_cursor({"asset_id": last.asset_id})
            assets = assets[:limit]
        return ListResponse(
            items=[asset_response(asset).model_dump() for asset in assets], next_cursor=next_cursor
        )

    @app.get("/api/v1/observations", response_model=ListResponse)
    def list_observations(
        session: Session = Depends(get_session),
        limit: int = Query(default=50, ge=1, le=200),
        asset_id: str | None = None,
        metric: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        cursor: str | None = None,
    ) -> ListResponse:
        statement = (
            select(Observation)
            .options(selectinload(Observation.asset))
            .order_by(Observation.observed_at, Observation.observation_id)
        )
        if asset_id:
            statement = statement.where(Observation.asset_id == asset_id)
        if metric:
            statement = statement.where(Observation.metric == metric)
        if start_at:
            statement = statement.where(Observation.observed_at >= start_at)
        if end_at:
            statement = statement.where(Observation.observed_at < end_at)
        if cursor:
            values = decode_cursor(cursor)
            try:
                after_at = datetime.fromisoformat(values["observed_at"])
                after_id = values["observation_id"]
            except (KeyError, ValueError):
                raise HTTPException(
                    status_code=422, detail="observation cursor is invalid"
                ) from None
            statement = statement.where(
                or_(
                    Observation.observed_at > after_at,
                    and_(
                        Observation.observed_at == after_at, Observation.observation_id > after_id
                    ),
                )
            )
        observations = list(session.scalars(statement.limit(limit + 1)))
        next_cursor = None
        if len(observations) > limit:
            last = observations[limit - 1]
            next_cursor = encode_cursor(
                {"observed_at": last.observed_at.isoformat(), "observation_id": last.observation_id}
            )
            observations = observations[:limit]
        return ListResponse(
            items=[
                observation_response(observation).model_dump(mode="json")
                for observation in observations
            ],
            next_cursor=next_cursor,
        )

    @app.get("/api/v1/findings", response_model=ListResponse)
    def list_findings(
        session: Session = Depends(get_session),
        limit: int = Query(default=50, ge=1, le=200),
        asset_id: str | None = None,
        status: str | None = None,
        cursor: str | None = None,
    ) -> ListResponse:
        statement = (
            select(Finding).options(selectinload(Finding.asset)).order_by(Finding.finding_id)
        )
        if asset_id:
            statement = statement.where(Finding.asset_id == asset_id)
        if status:
            statement = statement.where(Finding.status == status)
        if cursor:
            values = decode_cursor(cursor)
            finding_id = values.get("finding_id")
            if finding_id is None:
                raise HTTPException(status_code=422, detail="finding cursor is invalid")
            statement = statement.where(Finding.finding_id > finding_id)
        findings = list(session.scalars(statement.limit(limit + 1)))
        next_cursor = None
        if len(findings) > limit:
            last = findings[limit - 1]
            next_cursor = encode_cursor({"finding_id": last.finding_id})
            findings = findings[:limit]
        return ListResponse(
            items=[finding_response(finding).model_dump(mode="json") for finding in findings],
            next_cursor=next_cursor,
        )

    @app.get("/api/v1/operations/briefing", response_model=OperationsBriefingResponse)
    def get_operations_briefing(
        site_id: str = Query(min_length=1, max_length=128),
        session: Session = Depends(get_session),
    ) -> OperationsBriefingResponse:
        """Expose the public demo's stored evidence without inferred operating claims."""

        return operations_briefing_response(session, site_id)

    @app.get("/api/v1/incidents", response_model=ListResponse)
    def list_incidents(
        session: Session = Depends(get_session),
        limit: int = Query(default=50, ge=1, le=200),
        asset_id: str | None = None,
        status: str | None = None,
        cursor: str | None = None,
    ) -> ListResponse:
        statement = (
            select(Incident)
            .options(
                selectinload(Incident.asset),
                selectinload(Incident.finding_links),
            )
            .order_by(Incident.updated_at.desc(), Incident.incident_id)
        )
        if asset_id:
            statement = statement.where(Incident.asset_id == asset_id)
        if status:
            statement = statement.where(Incident.status == status)
        if cursor:
            values = decode_cursor(cursor)
            try:
                updated_at = datetime.fromisoformat(values["updated_at"])
                incident_id = values["incident_id"]
            except (KeyError, ValueError):
                raise HTTPException(status_code=422, detail="incident cursor is invalid") from None
            statement = statement.where(
                or_(
                    Incident.updated_at < updated_at,
                    and_(Incident.updated_at == updated_at, Incident.incident_id > incident_id),
                )
            )
        incidents = list(session.scalars(statement.limit(limit + 1)))
        next_cursor = None
        if len(incidents) > limit:
            last = incidents[limit - 1]
            next_cursor = encode_cursor(
                {"updated_at": last.updated_at.isoformat(), "incident_id": last.incident_id}
            )
            incidents = incidents[:limit]
        return ListResponse(
            items=[incident_response(incident).model_dump(mode="json") for incident in incidents],
            next_cursor=next_cursor,
        )

    @app.get("/api/v1/incidents/{incident_id}", response_model=IncidentDetailResponse)
    def get_incident(
        incident_id: str, session: Session = Depends(get_session)
    ) -> IncidentDetailResponse:
        incident = session.scalar(
            select(Incident)
            .options(
                selectinload(Incident.asset),
                selectinload(Incident.finding_links)
                .selectinload(IncidentFinding.finding)
                .selectinload(Finding.asset),
                selectinload(Incident.timeline_entries),
            )
            .where(Incident.incident_id == incident_id)
        )
        if incident is None:
            raise HTTPException(status_code=404, detail="incident not found")
        evidence_ids = linked_observation_ids(incident)
        linked_observations = (
            list(
                session.scalars(
                    select(Observation)
                    .options(selectinload(Observation.asset))
                    .where(Observation.observation_id.in_(evidence_ids))
                )
            )
            if evidence_ids
            else []
        )
        return incident_detail_response(incident, linked_observations)

    @app.post(
        "/api/v1/incidents/{incident_id}/transitions",
        response_model=IncidentDetailResponse,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
        },
    )
    def transition_incident_route(
        incident_id: str,
        transition: IncidentTransitionRequest,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
        session: Session = Depends(get_session),
    ) -> IncidentDetailResponse:
        with session.begin():
            incident = session.scalar(
                select(Incident)
                .options(
                    selectinload(Incident.asset),
                    selectinload(Incident.finding_links)
                    .selectinload(IncidentFinding.finding)
                    .selectinload(Finding.asset),
                    selectinload(Incident.timeline_entries),
                )
                .where(Incident.incident_id == incident_id)
            )
            if incident is None:
                raise HTTPException(status_code=404, detail="incident not found")
            transition_incident(session, incident, transition, idempotency_key, utc_now())
            session.flush()
            session.refresh(incident)
            # Refresh relationships after a new timeline entry was added.
            session.expire(incident, ["timeline_entries"])
            return incident_detail_response(incident)

    return app


app = create_app()
