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
	// Build output goes directly into Python package static directory
	build: {
		outDir: resolve(__dirname, "../src/asynctasq_monitor/static"),
		emptyOutDir: true,
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
	// Use absolute paths for production builds
	base: "/",
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
