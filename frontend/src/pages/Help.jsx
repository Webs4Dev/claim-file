import { FileText, Headphones, ListChecks } from "lucide-react";

const TOPICS = [
  {
    Icon: ListChecks,
    title: "Submitting a claim",
    body: "Choose \"New claim\", complete the four steps (policyholder, vehicle, accident, documents) and submit. You'll get a claim reference straight away.",
  },
  {
    Icon: FileText,
    title: "Documents we need",
    body: "The policy schedule, vehicle registration, driving licence and damage survey report are required. PDF or text files up to 10 MB are accepted.",
  },
  {
    Icon: Headphones,
    title: "Following up",
    body: "Open any claim to see its latest status. If more documents are requested, an upload prompt appears on the claim page. Status updates refresh automatically.",
  },
];

export default function Help() {
  return (
    <div className="help-page">
      <div className="form-page-head">
        <div className="eyebrow">
          <span /> HELP &amp; SUPPORT
        </div>
        <h1>How can we help?</h1>
        <p>Quick answers about using the ClaimFile portal.</p>
      </div>

      <div className="help-grid">
        {TOPICS.map(({ Icon, title, body }) => (
          <article className="panel help-card" key={title}>
            <Icon className="help-card-icon" size={22} />
            <h2>{title}</h2>
            <p>{body}</p>
          </article>
        ))}
      </div>

      <p className="help-note">
        Submitting a claim does not guarantee approval. Claims are assessed against
        the supplied evidence and your policy terms.
      </p>
    </div>
  );
}
