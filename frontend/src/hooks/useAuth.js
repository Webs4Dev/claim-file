import { useCallback, useEffect, useState } from "react";
import { getCurrentUser, onUnauthorized, register, signIn, signOut } from "../api";

/**
 * The signed-in user, from the session cookie.
 * user: undefined = still checking, null = signed out, object = signed in.
 */
export default function useAuth() {
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((me) => active && setUser(me))
      .catch(() => active && setUser(null));
    // Any 401 from the API (e.g. the session expired) signs the user out.
    onUnauthorized(() => setUser(null));
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    setUser(await signIn(email, password));
  }, []);

  const createAccount = useCallback(async (name, email, password) => {
    setUser(await register(name, email, password));
  }, []);

  const logout = useCallback(async () => {
    try {
      await signOut();
    } finally {
      setUser(null);
    }
  }, []);

  return { user, login, createAccount, logout };
}
