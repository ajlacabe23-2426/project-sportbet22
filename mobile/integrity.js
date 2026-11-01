"use strict";
// Offline byte-identity check for the local CSV and a separately imported audit.
// SHA-256 establishes byte equality only. It does not certify data authenticity,
// completeness, source rights or statistical validity.
(function(root){
  async function sha256ArrayBuffer(bytes,cryptoProvider=root.crypto){
    if(Object.prototype.toString.call(bytes)!=="[object ArrayBuffer]")
      throw new TypeError("SHA-256 requires original file bytes");
    if(!cryptoProvider?.subtle?.digest)return null;
    const digest=await cryptoProvider.subtle.digest("SHA-256",bytes);
    return Array.from(new Uint8Array(digest),byte=>byte.toString(16).padStart(2,"0")).join("");
  }
  function assessAuditLink(audit,dataset,selectedPlayer,selectedStat){
    if(!dataset)return {status:"NO_DATASET",description:"No local game-log CSV loaded. Audit results are standalone and not matched to a dataset."};
    if(!dataset.sha256)return {status:"HASH_UNAVAILABLE",description:"This browser cannot compute a SHA-256 for the loaded CSV. Dataset identity has not been verified."};
    if(dataset.sha256!==audit.dataset_sha256)
      return {status:"HASH_MISMATCH",description:"Dataset mismatch: the loaded CSV bytes differ from the audit's input. These results do not describe the loaded dataset."};
    if(!dataset.players.includes(audit.player_id))
      return {status:"PLAYER_MISMATCH",description:"Input CSV bytes match, but the audited player is missing from the selected player records. Review the source."};
    if(selectedPlayer!==audit.player_id||selectedStat!==audit.stat)
      return {status:"SELECTION_MISMATCH",description:"Input CSV SHA-256 matches the audit, but the selected player or statistic differs. Change the filters to compare the same context."};
    return {status:"BYTES_MATCHED",description:"Input CSV SHA-256 and selected player/statistic match the imported audit. Source authenticity, rights, completeness and model calibration remain unverified."};
  }
  const api={sha256ArrayBuffer,assessAuditLink};
  root.SportProbIntegrity=api;
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
})(typeof window!=="undefined"?window:globalThis);
