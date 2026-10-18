const messages = [
  { side: "them", text: "@Billo I hurt my knee. Where can I go without a surprise bill?" },
  { side: "billo", text: "I found 3 nearby options. Westwood Urgent Care is open now and usually costs about $240." },
  { side: "them", text: "@Billo save that one and keep track during the visit." },
  { side: "billo", text: "Saved. I’ll keep the estimate beside the visit record. You approve every next step." },
];

export default function ChatPreview() {
  return (
    <div className="phone-shell" aria-label="Example group chat with Billo">
      <div className="phone-top">
        <span className="status-dot" />
        <div><strong>Care group</strong><small>3 people · Billo</small></div>
        <span className="phone-menu">•••</span>
      </div>
      <div className="chat-date">Today 10:42 AM</div>
      <div className="messages">
        {messages.map((message, index) => (
          <div className={`message ${message.side}`} key={index}>
            {message.side === "billo" && <span className="mini-mark">@</span>}
            <p>{message.text}</p>
          </div>
        ))}
      </div>
      <div className="composer"><span>Tag @Billo…</span><button aria-label="Send example message">↑</button></div>
      <p className="chat-note">Billo only responds when someone tags @Billo.</p>
    </div>
  );
}
