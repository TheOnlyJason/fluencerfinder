import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./auth";
import { SelectionProvider } from "./selection";
import { GroupsProvider } from "./groupsContext";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <GroupsProvider>
          <SelectionProvider>
            <App />
          </SelectionProvider>
        </GroupsProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
