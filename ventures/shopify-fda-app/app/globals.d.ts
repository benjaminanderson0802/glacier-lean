declare module "*.css";

declare namespace JSX {
  interface IntrinsicElements {
    "s-app-nav": import("react").DetailedHTMLProps<import("react").HTMLAttributes<HTMLElement>, HTMLElement>;
  }
}
