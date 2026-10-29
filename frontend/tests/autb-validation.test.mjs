import test from "node:test";
import assert from "node:assert/strict";

import {
  validateSignIn,
  validateSignUp,
} from "../src/lib/auth-validation.mjs";

test("sign-in rejects a missing email", () => {
  const result = validateSignIn({
    email: "",
    password: "password123",
  });

  assert.equal(result.valid, false);
  assert.ok(result.errors.email);
});

test("sign-in rejects a malformed email", () => {
  const result = validateSignIn({
    email: "not-an-email",
    password: "password123",
  });

  assert.equal(result.valid, false);
  assert.ok(result.errors.email);
});

test("sign-in rejects a missing password", () => {
  const result = validateSignIn({
    email: "doctor@example.com",
    password: "",
  });

  assert.equal(result.valid, false);
  assert.ok(result.errors.password);
});

test("sign-in accepts valid inputs", () => {
  const result = validateSignIn({
    email: "doctor@example.com",
    password: "password123",
  });

  assert.equal(result.valid, true);
  assert.deepEqual(result.errors, {});
});

test("sign-up rejects a missing name", () => {
  const result = validateSignUp({
    name: "",
    email: "doctor@example.com",
    password: "password123",
    confirmPassword: "password123",
  });

  assert.equal(result.valid, false);
  assert.ok(result.errors.name);
});

test("sign-up rejects a missing email", () => {
  const result = validateSignUp({
    name: "Dr. Smith",
    email: "",
    password: "password123",
    confirmPassword: "password123",
  });

  assert.equal(result.valid, false);
  assert.ok(result.errors.email);
});

test("sign-up rejects a malformed email", () => {
  const result = validateSignUp({
    name: "Dr. Smith",
    email: "invalid-email",
    password: "password123",
    confirmPassword: "password123",
  });

  assert.equal(result.valid, false);
  assert.ok(result.errors.email);
});

test("sign-up rejects a password shorter than 8 characters", () => {
  const result = validateSignUp({
    name: "Dr. Smith",
    email: "doctor@example.com",
    password: "short",
    confirmPassword: "short",
  });

  assert.equal(result.valid, false);
  assert.ok(result.errors.password);
});

test("sign-up rejects mismatched confirmation passwords", () => {
  const result = validateSignUp({
    name: "Dr. Smith",
    email: "doctor@example.com",
    password: "password123",
    confirmPassword: "different123",
  });

  assert.equal(result.valid, false);
  assert.ok(result.errors.confirmPassword);
});

test("sign-up accepts valid inputs", () => {
  const result = validateSignUp({
    name: "Dr. Smith",
    email: "doctor@example.com",
    password: "password123",
    confirmPassword: "password123",
  });

  assert.equal(result.valid, true);
  assert.deepEqual(result.errors, {});
});
