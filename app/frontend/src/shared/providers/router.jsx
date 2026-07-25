import { createBrowserRouter } from "react-router-dom";
import { RootLayout } from "@/shared/layouts/root-layout";
import { NotFound } from "@/shared/pages/not-found";
import { RouteError } from "@/shared/pages/route-error";
import { PrintPage } from "@/features/print/pages/print-page";
import { InventoryPrintPage } from "@/features/inventory/pages/inventory-print-page";
import { InventoryEntryPrintPage } from "@/features/inventory/pages/inventory-entry-print-page";
import { SettingsPage } from "@/features/settings/pages/settings-page";
import { HistoryPage } from "@/features/history/pages/history-page";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <PrintPage /> },
      { path: "inventory-print", element: <InventoryPrintPage /> },
      { path: "inventory-entry-print", element: <InventoryEntryPrintPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "history", element: <HistoryPage /> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
