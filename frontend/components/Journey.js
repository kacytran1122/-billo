const stages = [
  { number: "01", label: "Before care", title: "Compare before you choose", text: "Describe what happened in plain words. Billo checks urgent warning signs, nearby options, and typical prices." },
  { number: "02", label: "During care", title: "Keep a simple visit record", text: "Tag @Billo as services happen. Your estimate and running total stay together, without silent decisions." },
  { number: "03", label: "After care", title: "Turn the bill into next steps", text: "Send the receipt or bill. Billo organizes payment status, benefit paths, and anything that needs your approval." },
];

export default function Journey() {
  return (
    <div className="journey-grid">
      {stages.map((stage) => (
        <article className="journey-card" key={stage.number}>
          <div className="journey-number">{stage.number}</div>
          <p className="eyebrow">{stage.label}</p>
          <h3>{stage.title}</h3>
          <p>{stage.text}</p>
          <span className="journey-arrow" aria-hidden="true">→</span>
        </article>
      ))}
    </div>
  );
}
