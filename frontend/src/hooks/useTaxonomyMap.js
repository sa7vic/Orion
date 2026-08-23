import { useEffect, useState } from "react";
import api from "../api";

/** Fetches the taxonomy once and returns a { attack_id: display_name } map,
 * so every screen shows "Agentic Payment-Agent Abuse" instead of the raw
 * "agentic_prompt_injection" id -- previously some screens showed one,
 * some showed the other, which read as an inconsistent product. */
export default function useTaxonomyMap() {
  const [map, setMap] = useState({});
  const [entries, setEntries] = useState([]);

  useEffect(() => {
    api.taxonomy()
      .then((r) => {
        setEntries(r.entries);
        const m = {};
        r.entries.forEach((e) => { m[e.attack_id] = e.display_name; });
        setMap(m);
      })
      .catch(() => {});
  }, []);

  const displayName = (attackId) => map[attackId] || attackId;

  return { map, entries, displayName };
}
