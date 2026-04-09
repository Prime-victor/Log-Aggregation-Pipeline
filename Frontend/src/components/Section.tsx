import React from "react";

type SectionProps = {
  id: string;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
};

const Section = ({ id, title, subtitle, actions, children }: SectionProps) => {
  return (
    <section id={id} className="section">
      <div className="section-header">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p className="section-subtitle">{subtitle}</p> : null}
        </div>
        {actions ? <div className="section-actions">{actions}</div> : null}
      </div>
      <div className="section-body">{children}</div>
    </section>
  );
};

export default Section;
