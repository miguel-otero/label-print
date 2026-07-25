import { Skeleton } from "@/shared/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";

// Tabla declarativa reutilizable. `columns` describe cada columna con:
//   { key, header?, headClassName?, cellClassName?, render(item) }
// y maneja los estados de carga (skeleton) y vacío.
export function TableRender({
  columns,
  items,
  loading = false,
  emptyMessage = "Sin resultados.",
  rowKey,
  rowProps,
  skeletonRows = 4,
  skeletonCellClassName = "h-5 w-full",
  tableClassName,
  containerClassName,
}) {
  const colSpan = columns.length;

  return (
    <Table className={tableClassName} containerClassName={containerClassName}>
      <TableHeader>
        <TableRow>
          {columns.map((column) => (
            <TableHead key={column.key} className={column.headClassName}>
              {column.header}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {loading ? (
          Array.from({ length: skeletonRows }).map((_, index) => (
            <TableRow key={index}>
              <TableCell colSpan={colSpan}>
                <Skeleton className={skeletonCellClassName} />
              </TableCell>
            </TableRow>
          ))
        ) : items.length === 0 ? (
          <TableRow>
            <TableCell colSpan={colSpan} className="h-24 text-center text-sm text-muted-foreground">
              {emptyMessage}
            </TableCell>
          </TableRow>
        ) : (
          items.map((item, index) => (
            <TableRow key={rowKey ? rowKey(item, index) : index} {...(rowProps?.(item) ?? {})}>
              {columns.map((column) => (
                <TableCell key={column.key} className={column.cellClassName}>
                  {column.render(item)}
                </TableCell>
              ))}
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}
