import backlog from "../data/backlog.json";
import researchSources from "../data/sources.json";
import engineeringSources from "../data/engineering-sources.json";
import type {Task, Source} from "./types";
export const initialTasks = backlog as Task[];
export const sources: Source[] = [...researchSources, ...engineeringSources];
export const meta = {
  baselineCommit: "0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f",
  repositoryUrl: "https://github.com/erikbabcan-commits/forenzx-mcp-hub",
  productPrice: 19,
  deadline: "Nie je určený externý deadline",
};

