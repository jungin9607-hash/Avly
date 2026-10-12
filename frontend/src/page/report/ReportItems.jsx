import Icon from "../../components/ui/Icon";

export function ReasonItem({ number, title, badge, highlight, text }) {
  return (
    <div className="reason-item">
      <div className={`reason-number ${highlight ? "highlight" : ""}`}>{number}</div>

      <div className="reason-content">
        <div className="reason-header">
          <strong>{title}</strong>
          <span className={highlight ? "blue-badge" : undefined}>{badge}</span>
        </div>
        <p>{text}</p>
      </div>
    </div>
  );
}

export function TelemetryItem({ icon, label, value, note, tone }) {
  return (
    <div className="telemetry-item">
      <div className={`telemetry-icon ${tone === "danger" ? "danger" : ""}`}>
        <Icon name={icon} />
      </div>

      <div>
        <p>{label}</p>
        <strong>
          {value}
          <small className={tone === "danger" ? "danger-text" : "safe"}>{note}</small>
        </strong>
      </div>
    </div>
  );
}

export function EvidenceItem({ title, badge, text, images, detail }) {
  const body = (
    <div className="evidence-content">
      <div className="evidence-title">
        <strong>{title}</strong>
        <span className={badge.className}>{badge.text}</span>
      </div>

      <p>{text}</p>

      {detail && (
        <div className={`evidence-detail ${detail.className ?? ""}`.trim()}>
          <Icon name={detail.icon} />
          {detail.text}
        </div>
      )}
    </div>
  );

  if (!images) {
    return (
      <div className="evidence-item simple">
        <Icon name="check_circle" className="check" />
        {body}
      </div>
    );
  }

  return (
    <div className="evidence-item">
      <div className="evidence-heading">
        <Icon name="check_circle" className="check" />
        {body}
      </div>

      <div className="evidence-images">
        {images.map((image, index) => (
          <div className="evidence-image" key={image.time}>
            <img src={image.src} alt={`사고 증거 ${index + 1}`} />
            <span>{image.time}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
