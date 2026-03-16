import type { ReactNode } from "react";

export function DevPageHeader({
  stage,
  title,
  description,
  facts,
}: {
  stage: string;
  title: string;
  description: string;
  facts: Array<{ label: string; value: ReactNode }>;
}) {
  return (
    <section className="hero-card">
      <div className="hero-grid">
        <div>
          <p className="eyebrow">{stage}</p>
          <h2>{title}</h2>
          <p className="lede">{description}</p>
        </div>

        <dl className="console-facts">
          {facts.map((fact) => (
            <div key={fact.label}>
              <dt>{fact.label}</dt>
              <dd>{fact.value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
