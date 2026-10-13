"use client";

import { useParams } from "next/navigation";
import { ChatView } from "@/components/chat-view";

export default function Conversation() {
  const params = useParams<{ id: string }>();

  return <ChatView id={params.id} />;
}