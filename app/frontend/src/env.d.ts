/// <reference types="vite/client" />

// Declaraciones para que el editor resuelva JSX sin node_modules local
// (las dependencias reales viven dentro del contenedor Docker)
declare module "react/jsx-runtime" {
  const content: any;
  export default content;
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

declare module "react/jsx-dev-runtime" {
  const content: any;
  export default content;
  export const jsxDEV: any;
  export const Fragment: any;
}
