export default function Metric({ Icon, title, value, note, tone }) {
  return (
    <article className="metric-card">
      <div className={`metric-icon ${tone}`}>
        <Icon size={19} />
      </div>
      <div className="metric-label">{title}</div>
      <div className="metric-value">{value}</div>
      <div className="metric-note">{note}</div>
    </article>
  );
}
