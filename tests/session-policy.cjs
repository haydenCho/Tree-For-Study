const assert=require('node:assert/strict');
const {sessionOutcome}=require('../ui/SessionPolicy.js');
for(const [minutes,count,size] of [[20,1,'small'],[40,2,'small'],[49,2,'small'],[50,2,'large'],[60,3,'large'],[180,9,'large']]){
  const actual=sessionOutcome(minutes);assert.equal(actual.earnedCount,count);assert.equal(actual.size,size);assert.equal(actual.creditedSeconds,minutes*60);
}
assert.equal(sessionOutcome(30).earnedCount*2,2);
const abandoned=sessionOutcome(60,'abandoned');assert.equal(abandoned.earnedCount,0);assert.equal(abandoned.creditedSeconds,0);assert.equal(abandoned.reservedCount,3);assert.equal(abandoned.state,'wilted');
assert.equal(sessionOutcome(60,'paused').creditedSeconds,0);
assert.equal(sessionOutcome(50).creditedSeconds,3000);
for(const invalid of [0,19,181,40.5,NaN])assert.throws(()=>sessionOutcome(invalid));
console.log('Session policy: boundaries, no carry-over, abandoned zero and input limits passed');
