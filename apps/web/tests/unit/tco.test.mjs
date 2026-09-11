import test from 'node:test';
import assert from 'node:assert/strict';
import {calculateTco,componentKeys,parseCost} from '../../src/lib/tco.ts';
const costs=()=>({...Object.fromEntries(componentKeys.map(key=>[key,'0'])),panel_count:'100',period_years:'3',currency:'TEST',gateway:'100',shared_server:'1000',maintenance_annual:'10',battery_annual:'5'});
test('empty, partial and invalid costs never become fabricated zero-valued estimates',()=>{
 assert.equal(calculateTco({}).ready,false);
 const input=costs();delete input.installation;assert.equal(calculateTco(input).ready,false);
 for(const bad of ['', ' ', 'NaN', 'Infinity', '-1'])assert.equal(parseCost(bad),null);
 assert.equal(parseCost('0'),0);
});
test('zero/noninteger panel count, missing currency and nonpositive horizon cannot divide or calculate',()=>{
 for(const count of ['0','-1','1.5','Infinity'])assert.equal(calculateTco({...costs(),panel_count:count}).ready,false);
 for(const years of ['0','-3',''])assert.equal(calculateTco({...costs(),period_years:years}).ready,false);
 assert.equal(calculateTco({...costs(),currency:''}).ready,false);
});
test('shared server is counted once and annual maintenance is multiplied by the selected horizon',()=>{
 const result=calculateTco(costs());assert.equal(result.ready,true);
 assert.equal(result.perPanelInitial,110);assert.equal(result.perPanelAnnual,15);
 assert.equal(result.perPanelTotal,155);assert.equal(result.fleetTotal,15500);
 assert.equal(result.annualGross,null);assert.equal(result.paybackYears,null);
});
test('all optional benefit inputs are required and payback requires strictly positive annual net benefit',()=>{
 const base={...costs(),outage_hour_cost:'10',maintenance_visit_cost:'5',avoided_hours:'3',avoided_visits:'1'};
 const result=calculateTco(base);assert.equal(result.annualGross,35);assert.equal(result.annualNet,20);assert.equal(result.paybackYears,5.5);
 for(const missing of ['outage_hour_cost','maintenance_visit_cost','avoided_hours','avoided_visits'])assert.equal(calculateTco({...base,[missing]:''}).paybackYears,null);
 assert.equal(calculateTco({...base,avoided_hours:'1',avoided_visits:'1'}).paybackYears,null);
 assert.equal(calculateTco({...base,avoided_hours:'0',avoided_visits:'0'}).paybackYears,null);
});
test('overflowed totals do not produce an infinite investment claim',()=>{
 assert.equal(calculateTco({...costs(),gateway:'1e308',panel_count:'1000'}).ready,false);
});
