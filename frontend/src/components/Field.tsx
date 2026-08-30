export function Field({ label, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return <label className="block text-sm font-medium">{label}<input className="mt-2 h-11 w-full rounded-lg border bg-background px-3 text-sm placeholder:text-muted-foreground" {...props} /></label>
}
