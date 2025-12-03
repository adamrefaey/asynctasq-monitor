import { resolve } from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
	plugins: [
		react({
			babel: {
				plugins: [["babel-plugin-react-compiler"]],
			},
		}),
		tailwindcss(),
	],
	resolve: {
		alias: {
			"@": resolve(__dirname, "./src"),
		},
	},
	build: {
		rollupOptions: {
			output: {
				manualChunks: {
					// Vendor chunks for better caching
					"react-vendor": ["react", "react-dom", "react-router-dom"],
					"query-vendor": ["@tanstack/react-query", "@tanstack/react-query-devtools"],
					"ui-vendor": ["react-aria-components", "tailwind-variants", "tailwind-merge"],
					"chart-vendor": ["recharts"],
					"utils-vendor": ["date-fns", "zod", "zustand"],
				},
			},
		},
	},
	server: {
		proxy: {
			"/api": {
				target: "http://localhost:8000",
				changeOrigin: true,
			},
			"/ws": {
				target: "ws://localhost:8000",
				ws: true,
			},
		},
	},
});
