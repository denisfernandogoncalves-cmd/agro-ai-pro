import React from "react";
import ReactDOM from "react-dom/client";

import AppEnterprise from "./AppEnterprise";
import { registrarPwa } from "./pwa";

import "leaflet/dist/leaflet.css";
import "./pages/Clima/clima.css";
import "./styles/app-enterprise.css";

void registrarPwa();

ReactDOM.createRoot(
  document.getElementById("root")!
).render(
  <React.StrictMode>
    <AppEnterprise />
  </React.StrictMode>
);
