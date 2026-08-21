import { chromium } from "playwright";
import { writeFile } from "node:fs/promises";

const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1440,height:900}});
await page.goto("http://127.0.0.1:8765/Avatar/avatar_builder/proofs/neutral_adult_foundation_20260728/threejs_preview/",{waitUntil:"networkidle"});
await page.waitForFunction(()=>window.__AVATAR_PROOF__?.loaded===true,{timeout:30000});
await page.waitForTimeout(1500);
const result=await page.evaluate(()=>window.__AVATAR_PROOF__);
await page.screenshot({path:"../avatar_builder/proofs/neutral_adult_foundation_20260728/threejs_preview/runtime_screenshot.png",fullPage:true});
await writeFile("../avatar_builder/proofs/neutral_adult_foundation_20260728/GLB_RUNTIME_VALIDATION_REPORT.json",JSON.stringify({
  status:result.loaded&&result.meshes>=6&&result.bones>=50?"PARTIAL":"FAILED",
  note:"Static neutral GLB browser load proven. Animation library export remains a separate blocked item when animations is zero.",
  ...result,runtime_activation_allowed:false,Kira_body_replaced:false
},null,2)+"\n");
await browser.close();
