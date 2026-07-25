import { Outlet } from "react-router-dom";

export function RootLayout() {
  // Punto de montaje de las rutas hijas.
  return <Outlet />;
}
