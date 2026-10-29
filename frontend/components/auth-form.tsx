"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authClient } from "@/src/lib/auth-client";
import Link from "next/link";

type AuthFormProps = {
    mode: "sign-in" | "sign-up";
};

export default function AuthForm({ mode }: AuthFormProps) {
    const router = useRouter();
    const isSignUp = mode === "sign-up";

    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    return (
        <form
            className="space-y-4"
            onSubmit={async (event) => {
                event.preventDefault();
                setError("");

                // Validate input before submitting.
                if (isSignUp && !name.trim()) {
                    setError("Please enter your name.");
                    return;
                }

                const normalizedEmail = email.trim();

                if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
                    setError("Please enter a valid email address.");
                    return;
                }

                if (password.length < 8) {
                    setError("Password must be at least 8 characters.");
                    return;
                }

                if (isSignUp && password !== confirmPassword) {
                    setError("Passwords do not match.");
                    return;
                }

                setIsLoading(true);

                try {
                    const result = isSignUp
                        ? await authClient.signUp.email({
                            name: name.trim(),
                            email: normalizedEmail,
                            password,
                            callbackURL: "/timeline",
                        })
                        : await authClient.signIn.email({
                            email: normalizedEmail,
                            password,
                            callbackURL: "/timeline",
                        });

                    if (result.error) {
                        setError(
                            result.error.message ||
                            "Authentication failed. Please try again."
                        );
                        return;
                    }

                    router.push("/timeline");
                    router.refresh();
                } catch {
                    setError(
                        "Something went wrong. Please check your connection and try again."
                    );
                } finally {
                    setIsLoading(false);
                }
            }}
        >
            <h1 className="text-2xl font-semibold">
                {isSignUp ? "Create your account" : "Sign in to MEDIRounds"}
            </h1>

            {isSignUp && (
                <div>
                    <label htmlFor="name" className="mb-1 block">
                        Full name
                    </label>
                    <input
                        id="name"
                        name="name"
                        type="text"
                        autoComplete="name"
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        required
                        disabled={isLoading}
                        className="w-full rounded border p-2"
                    />
                </div>
            )}

            <div>
                <label htmlFor="email" className="mb-1 block">
                    Email
                </label>
                <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                    disabled={isLoading}
                    className="w-full rounded border p-2"
                />
            </div>

            <div>
                <label htmlFor="password" className="mb-1 block">
                    Password
                </label>
                <input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete={isSignUp ? "new-password" : "current-password"}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    minLength={8}
                    required
                    disabled={isLoading}
                    className="w-full rounded border p-2"
                />
            </div>

            {isSignUp && (
                <div>
                    <label htmlFor="confirmPassword" className="mb-1 block">
                        Confirm password
                    </label>
                    <input
                        id="confirmPassword"
                        name="confirmPassword"
                        type="password"
                        autoComplete="new-password"
                        value={confirmPassword}
                        onChange={(event) => setConfirmPassword(event.target.value)}
                        required
                        disabled={isLoading}
                        className="w-full rounded border p-2"
                    />
                </div>
            )}

            {error && (
                <p role="alert" className="text-sm text-red-600">
                    {error}
                </p>
            )}

            <button
                type="submit"
                disabled={isLoading}
                className="w-full rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
                {isLoading
                    ? "Please wait..."
                    : isSignUp
                        ? "Create account"
                        : "Sign in"}
            </button>

            <p className="text-center text-sm text-gray-600">
                {isSignUp ? (
                    <>
                        Already have an account?{" "}
                        <Link
                            href="/sign-in"
                            className="font-medium text-blue-600 hover:underline"
                        >
                            Sign in
                        </Link>
                    </>
                ) : (
                    <>
                        Don't have an account?{" "}
                        <Link
                            href="/sign-up"
                            className="font-medium text-blue-600 hover:underline"
                        >
                            Create account
                        </Link>
                    </>
                )}
            </p>
        </form >
    );
}