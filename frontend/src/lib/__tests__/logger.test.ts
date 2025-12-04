/**
 * Tests for the logger utility module.
 *
 * Tests verify:
 * - Logging functions are available
 * - Error logging always works
 * - Logger exports the expected interface
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { logger } from "../logger";

describe("Logger", () => {
	let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

	beforeEach(() => {
		vi.spyOn(console, "log").mockImplementation(() => {});
		vi.spyOn(console, "warn").mockImplementation(() => {});
		consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe("interface", () => {
		it("exports log function", () => {
			expect(typeof logger.log).toBe("function");
		});

		it("exports warn function", () => {
			expect(typeof logger.warn).toBe("function");
		});

		it("exports error function", () => {
			expect(typeof logger.error).toBe("function");
		});
	});

	describe("error logging (always enabled)", () => {
		it("error() writes to console.error", () => {
			logger.error("error message");
			expect(consoleErrorSpy).toHaveBeenCalledWith("error message");
		});

		it("error() handles multiple arguments", () => {
			logger.error("Failed:", { code: 500 }, "details");
			expect(consoleErrorSpy).toHaveBeenCalledWith("Failed:", { code: 500 }, "details");
		});

		it("error() handles Error objects", () => {
			const testError = new Error("test error");
			logger.error("Caught:", testError);
			expect(consoleErrorSpy).toHaveBeenCalledWith("Caught:", testError);
		});
	});

	describe("development logging", () => {
		// In test environment, import.meta.env.DEV is typically true
		// These tests verify the functions work when called

		it("log() can be called without errors", () => {
			expect(() => logger.log("test message")).not.toThrow();
		});

		it("log() handles multiple arguments", () => {
			expect(() => logger.log("message", { data: 123 }, ["array"])).not.toThrow();
		});

		it("warn() can be called without errors", () => {
			expect(() => logger.warn("warning message")).not.toThrow();
		});

		it("warn() handles multiple arguments", () => {
			expect(() => logger.warn("warning:", { level: "high" })).not.toThrow();
		});
	});

	describe("edge cases", () => {
		it("handles undefined arguments", () => {
			expect(() => logger.log(undefined)).not.toThrow();
			expect(() => logger.error(undefined)).not.toThrow();
		});

		it("handles null arguments", () => {
			expect(() => logger.log(null)).not.toThrow();
			expect(() => logger.error(null)).not.toThrow();
		});

		it("handles no arguments", () => {
			expect(() => logger.log()).not.toThrow();
			expect(() => logger.warn()).not.toThrow();
			expect(() => logger.error()).not.toThrow();
		});

		it("handles complex nested objects", () => {
			const complexObj = {
				nested: { deep: { value: 42 } },
				array: [1, 2, { three: 3 }],
			};
			expect(() => logger.log(complexObj)).not.toThrow();
		});

		it("handles functions as arguments", () => {
			const fn = () => "test";
			expect(() => logger.log("function:", fn)).not.toThrow();
		});

		it("handles symbols", () => {
			const sym = Symbol("test");
			expect(() => logger.log("symbol:", sym)).not.toThrow();
		});
	});
});
