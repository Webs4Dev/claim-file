import { useCallback, useEffect, useState } from "react";

/**
 * Tiny hash router so the browser back button, refresh and deep links work.
 *   #/            dashboard
 *   #/claims      claims list
 *   #/new         new claim form
 *   #/claims/ID   claim details
 *   #/help        help
 */
function parse() {
  const [first = "", second] = window.location.hash
    .replace(/^#\/?/, "")
    .split("/");
  if (first === "claims" && second) {
    return { page: "details", claimId: decodeURIComponent(second) };
  }
  if (["claims", "new", "help"].includes(first)) {
    return { page: first, claimId: "" };
  }
  return { page: "dashboard", claimId: "" };
}

export default function useHashRoute() {
  const [route, setRoute] = useState(parse);

  useEffect(() => {
    const onChange = () => {
      setRoute(parse());
      window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const navigate = useCallback((path) => {
    window.location.hash = path;
  }, []);

  return { ...route, navigate };
}
