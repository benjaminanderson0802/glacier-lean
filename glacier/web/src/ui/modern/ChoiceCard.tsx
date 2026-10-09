export function ChoiceCard({ question, choices, onSelect }: { question: string; choices: string[]; onSelect: (choice: string) => void }) {
  return <section className="thread-choice-card"><div className="thread-choice-label">A quick question</div><p>{question}</p><div className="thread-choices">{choices.map(choice => <button type="button" key={choice} onClick={() => onSelect(choice)}>{choice}</button>)}</div></section>
}
