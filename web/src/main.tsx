import { createRoot } from "react-dom/client";
import "react-isokit/styles.css";
import IspPipeline from "./components/ui/isp-pipeline";

const root = document.getElementById("pipeline-root");
if (root) createRoot(root).render(<IspPipeline />);
