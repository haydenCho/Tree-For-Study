// Display helper only. The server must independently validate this policy.
function sessionOutcome(minutes, status = 'completed') {
  if (!Number.isInteger(minutes) || minutes < 20 || minutes > 180) throw new RangeError('20~180분 정수');
  const reservedCount = Math.floor(minutes / 20);
  const size = minutes >= 50 ? 'large' : 'small';
  return {reservedCount, size, earnedCount: status === 'completed' ? reservedCount : 0, creditedSeconds: status === 'completed' ? minutes * 60 : 0, state: status === 'abandoned' ? 'wilted' : status === 'completed' ? 'normal' : 'seedling'};
}
if (typeof module !== 'undefined') module.exports = {sessionOutcome};
