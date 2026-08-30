export function PipelineLog({ lines }: { lines: string[] }) {
  return <div className="rounded-lg border bg-background p-3 font-mono text-[11px] leading-5 text-muted-foreground">
    {lines.map((line) => <div className="flex gap-2" key={line}><span className="text-primary">&gt;</span><span>{line}</span></div>)}
  </div>
}
