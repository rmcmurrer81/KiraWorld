/** Opt-in mount seam; importing this file neither mounts UI nor plays audio. */
import {mountMarsHistoryLibrary} from '../candidate/mars-history-library.mjs';
export function mountCrewQuartersListeningPoint(container,officialManifest,{onInteractionChange}={}){
 return mountMarsHistoryLibrary(container,{manifest:officialManifest,onInteractionChange});
}
