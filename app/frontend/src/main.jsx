import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { router } from "@/shared/providers/router";
import { ThemeProvider } from "@/shared/providers/theme";
import "./index.css";

const queryClient = new QueryClient();

const container = document.getElementById("root");
if (!container) throw new Error("No se encontró el elemento #root");
createRoot(container).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <RouterProvider router={router} />
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
);
