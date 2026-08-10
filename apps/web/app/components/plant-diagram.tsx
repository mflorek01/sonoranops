import { useEffect, useMemo, useState } from "react";
import type { OperationsBriefing } from "../../lib/api/types";
import { assetLabel, metricLabel, number, Panel, pretty, time } from "./shared";

type SensorState = NonNullable<
  NonNullable<OperationsBriefing["visualAnalytics"]>["sensorStates"]
>[number];

type DiagramView = "incidents" | "quality" | "explorer";

const plantOrder = [
  { key: "feeder", label: "Feeder" },
  { key: "primary-crusher", label: "Primary crusher" },
  { key: "conveyor", label: "Conveyor" },
  { key: "secondary-crusher", label: "Secondary crusher" },
  { key: "screen", label: "Screen" },
  { key: "stacker", label: "Stacker" },
  { key: "stockpile", label: "Stockpile" },
];

const stateText: Record<SensorState["state"], string> = {
  critical: "Critical issue linked",
  attention: "Needs attention",
  data_quality: "Data quality needs review",
  no_issue: "No issue found in this simulated shift",
  no_data: "No sensor data returned",
};
const stateRank: Record<SensorState["state"], number> = {
  critical: 0,
  attention: 1,
  data_quality: 2,
  no_issue: 3,
  no_data: 4,
};

function processKey(assetId: string) {
  return plantOrder.find((item) => assetId.includes(item.key))?.key;
}

function simpleReason(sensor: SensorState) {
  if (sensor.state === "critical") return "This sensor is linked to an open critical issue.";
  if (sensor.state === "attention") return "This sensor is linked to an issue that needs review.";
  if (sensor.state === "data_quality") return "This reading has a data warning.";
  if (sensor.state === "no_data") return "No sensor data was returned for this reading.";
  return "No issue or data warning was found for this sensor in this simulated shift.";
}

function SensorButton({
  sensor,
  selected,
  onSelect,
}: {
  sensor: SensorState;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      className={`sensor-dot sensor-${sensor.state}${selected ? " selected" : ""}`}
      onClick={onSelect}
      aria-pressed={selected}
    >
      <span aria-hidden="true" />
      {metricLabel(sensor.metric)}: {stateText[sensor.state]}
    </button>
  );
}

export function PlantDiagram({
  briefing,
  onView,
}: {
  briefing: OperationsBriefing;
  onView: (view: DiagramView) => void;
}) {
  const sensorStates = briefing.visualAnalytics?.sensorStates;
  const sensors = useMemo(() => sensorStates ?? [], [sensorStates]);
  const [selectedKey, setSelectedKey] = useState<string>();
  const selected = sensors.find(
    (sensor) => `${sensor.assetId}-${sensor.metric}` === selectedKey,
  );
  const mapped = useMemo(
    () => sensors.filter((sensor) => processKey(sensor.assetId)),
    [sensors],
  );
  const unmapped = useMemo(
    () => sensors.filter((sensor) => !processKey(sensor.assetId)),
    [sensors],
  );

  useEffect(() => {
    if (selectedKey || !sensors.length) return;
    const priority = [...sensors].sort(
      (left, right) =>
        stateRank[left.state] - stateRank[right.state] ||
        right.linkedActiveIncidentCount - left.linkedActiveIncidentCount ||
        left.metric.localeCompare(right.metric),
    )[0];
    setSelectedKey(`${priority.assetId}-${priority.metric}`);
  }, [selectedKey, sensors]);

  const nextStep: { label: string; view: DiagramView } = selected?.linkedActiveIncidentCount
    ? { label: "Open issues", view: "incidents" }
    : selected?.state === "data_quality"
      ? { label: "Review data quality", view: "quality" }
      : { label: "Inspect supporting evidence", view: "explorer" };

  return (
    <section className="plant-diagram-section" aria-labelledby="plant-diagram-title">
      <Panel
        title="Where to look"
        detail="Select a sensor to see its latest returned record and the reason for its status."
      >
        <p className="plant-intro" id="plant-diagram-title">
          This is the simulated material path used for review: feeder to stockpile. It is not a surveyed site map.
        </p>
        {!briefing.visualAnalytics?.sensorStates && (
          <p className="data-unavailable">
            Sensor status is not available in this API response. The issue and data-quality views remain available below.
          </p>
        )}
        <ol className="plant-flow">
          {plantOrder.map((node, index) => {
            const nodeSensors = mapped.filter((sensor) => processKey(sensor.assetId) === node.key);
            const assetId = nodeSensors[0]?.assetId;
            return (
              <li key={node.key}>
                <article>
                  <header>
                    <span>Step {index + 1}</span>
                    {assetId && <small>{assetLabel(assetId)}</small>}
                  </header>
                  <h3>{node.label}</h3>
                  {nodeSensors.length ? (
                    <div className="sensor-list">
                      {nodeSensors.map((sensor) => (
                        <SensorButton
                          key={`${sensor.assetId}-${sensor.metric}`}
                          sensor={sensor}
                          selected={selectedKey === `${sensor.assetId}-${sensor.metric}`}
                          onSelect={() => setSelectedKey(`${sensor.assetId}-${sensor.metric}`)}
                        />
                      ))}
                    </div>
                  ) : (
                    <p className="no-sensor">No sensor readings returned.</p>
                  )}
                </article>
              </li>
            );
          })}
        </ol>
        {unmapped.length > 0 && (
          <section className="unmapped-sensors" aria-labelledby="unmapped-sensors-title">
            <h3 id="unmapped-sensors-title">Other sensor readings</h3>
            <p>These readings are not placed on the simulated material path.</p>
            <div className="sensor-list">
              {unmapped.map((sensor) => (
                <SensorButton
                  key={`${sensor.assetId}-${sensor.metric}`}
                  sensor={sensor}
                  selected={selectedKey === `${sensor.assetId}-${sensor.metric}`}
                  onSelect={() => setSelectedKey(`${sensor.assetId}-${sensor.metric}`)}
                />
              ))}
            </div>
          </section>
        )}
      </Panel>
      {selected && (
        <Panel title="Selected sensor" detail={stateText[selected.state]}>
          <div className="sensor-detail">
            <div>
              <h3>{metricLabel(selected.metric)}</h3>
              <p>{assetLabel(selected.assetId)}</p>
              <dl>
                <div><dt>Latest reading</dt><dd>{number(selected.latestValue, 2)} {selected.unit ?? ""}</dd></div>
                <div><dt>Recorded at</dt><dd>{time(selected.latestObservedAt)}</dd></div>
                <div><dt>Linked records</dt><dd>{selected.linkedFindingCount.toLocaleString()} automated checks; {selected.linkedActiveIncidentCount.toLocaleString()} open issues</dd></div>
              </dl>
            </div>
            <div className={`sensor-status sensor-${selected.state}`}>
              <strong>{stateText[selected.state]}</strong>
              <p>{simpleReason(selected)}</p>
              {selected.latestQualityFlags.length > 0 && (
                <p>Latest record flags: {selected.latestQualityFlags.map(pretty).join(", ")}.</p>
              )}
              <button className="primary" onClick={() => onView(nextStep.view)}>{nextStep.label}</button>
            </div>
          </div>
          <details className="technical-details">
            <summary>Technical details</summary>
            <p>Asset ID: {selected.assetId}. Metric key: {selected.metric}. Returned readings: {selected.observationCount.toLocaleString()}. Readings with data warnings: {selected.flaggedObservationCount.toLocaleString()}. API reason: {selected.reason}</p>
          </details>
        </Panel>
      )}
    </section>
  );
}
