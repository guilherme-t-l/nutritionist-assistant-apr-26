import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./styles.css";

// `document.getElementById("root")!` grabs the <div id="root"> in
// index.html. The trailing `!` tells TypeScript "trust me, this is not
// null" — because we put that div there ourselves.
const root = createRoot(document.getElementById("root")!);

root.render(
  <StrictMode>
    <App />
  </StrictMode>,
);
