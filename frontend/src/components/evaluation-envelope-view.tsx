import type { EvaluationEnvelope } from "@/lib/contracts/evaluation-envelope";

function prettyJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

export function EvaluationEnvelopeView({
  envelope,
  emptyMessage,
}: {
  envelope: EvaluationEnvelope | null;
  emptyMessage: string;
}) {
  if (!envelope) {
    return <p className="status">{emptyMessage}</p>;
  }

  const { inputBuilder, evaluationSummary, whyPanel, protocolPanel, actionRail } = envelope.zones;

  return (
    <section className="envelope-stack">
      <dl className="summary-grid">
        <div>
          <dt>requestId</dt>
          <dd>{envelope.requestId}</dd>
        </div>
        <div>
          <dt>source</dt>
          <dd>{envelope.source}</dd>
        </div>
        <div>
          <dt>stage</dt>
          <dd>{evaluationSummary.stage}</dd>
        </div>
        <div>
          <dt>evaluationId</dt>
          <dd>{evaluationSummary.evaluationId || "missing"}</dd>
        </div>
      </dl>

      <div className="zone-grid">
        <section className="zone-card">
          <div className="panel-header">
            <h3>Input Builder</h3>
            <span>{inputBuilder.mode}</span>
          </div>
          <pre>{prettyJson(inputBuilder)}</pre>
        </section>

        <section className="zone-card">
          <div className="panel-header">
            <h3>Evaluation Summary</h3>
            <span>{evaluationSummary.label || "pending"}</span>
          </div>
          <pre>{prettyJson(evaluationSummary)}</pre>
        </section>

        <section className="zone-card">
          <div className="panel-header">
            <h3>Why Panel</h3>
            <span>explain + dna</span>
          </div>
          <pre>{prettyJson(whyPanel)}</pre>
        </section>

        <section className="zone-card">
          <div className="panel-header">
            <h3>Protocol Panel</h3>
            <span>{protocolPanel.triggered.length} protocols</span>
          </div>
          <pre>{prettyJson(protocolPanel)}</pre>
        </section>

        <section className="zone-card zone-card-wide">
          <div className="panel-header">
            <h3>Action Rail</h3>
            <span>{actionRail.suggestions.length} suggestions</span>
          </div>
          <pre>{prettyJson(actionRail)}</pre>
        </section>

        <section className="zone-card zone-card-wide">
          <div className="panel-header">
            <h3>Raw Contract Payload</h3>
            <span>adapter input</span>
          </div>
          <pre>{prettyJson(envelope.raw)}</pre>
        </section>
      </div>
    </section>
  );
}
