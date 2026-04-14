import { createContext, useContext, type ReactNode } from "react";

import { usePersistentState } from "@/hooks/use-persistent-state";

interface AppStateValue {
  userId: string;
  setUserId: (value: string) => void;
  activeDocId: string | null;
  setActiveDocId: (value: string | null) => void;
}

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = usePersistentState("mas:user-id", "demo_user");
  const [activeDocId, setActiveDocId] = usePersistentState<string | null>("mas:active-doc-id", null);

  return (
    <AppStateContext.Provider
      value={{
        userId,
        setUserId,
        activeDocId,
        setActiveDocId,
      }}
    >
      {children}
    </AppStateContext.Provider>
  );
}

export function useAppState() {
  const context = useContext(AppStateContext);

  if (!context) {
    throw new Error("useAppState must be used within AppStateProvider");
  }

  return context;
}
