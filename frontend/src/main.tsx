import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { QueryProvider } from "@/lib/query";
import { router } from "@/router";
import "./tailwind.css";

const rootElement = document.getElementById("root");
if (rootElement) {
	createRoot(rootElement).render(
		<StrictMode>
			<QueryProvider>
				<RouterProvider router={router} />
			</QueryProvider>
		</StrictMode>,
	);
}
