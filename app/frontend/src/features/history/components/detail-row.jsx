export function DetailRow({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b pb-2">
      <span className="text-xs uppercase text-muted-foreground">{label}</span>
      <span className="text-right">{value}</span>
    </div>
  );
}
