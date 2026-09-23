import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import vm from 'node:vm';
function loadKey(path){const source=readFileSync(new URL(path,import.meta.url),'utf8'),end=source.indexOf('export class FiniteTopDomain');assert(end>0);return vm.runInNewContext(source.slice(0,end)+';key',{},{timeout:1000});}
const oldKey=loadKey('./reference017/candidate/finite_top_domain.mjs'),newKey=loadKey('./candidate/finite_top_domain.mjs');
let cases=0,exceptions=0;const start=performance.now();
function call(fn,input){try{return {value:fn(input)}}catch(e){return {error:e.name}}}
function test(input){const before=Array.isArray(input)||ArrayBuffer.isView(input)?input.slice():input;const a=call(oldKey,input),b=call(newKey,input);assert.deepEqual(b,a);if(a.error)exceptions++;if(Array.isArray(input)||ArrayBuffer.isView(input))assert.deepEqual(input,before);cases++;}
const ints=[-Number.MAX_VALUE,-Number.MAX_SAFE_INTEGER,-1,-0,0,1,2,24,702,724,725,2147483647,Number.MAX_SAFE_INTEGER,Number.MAX_VALUE];
for(const a of ints){test([a]);for(const b of ints){test([a,b]);for(const c of ints)test([a,b,c]);}}
const fallback=[NaN,Infinity,-Infinity,.5,null,undefined,'','1',true,false,1n,Symbol('id')];
for(const v of fallback){test([v]);test([1,v]);test([v,1]);test([1,v,2]);test([v,2,1]);test([2,1,v]);}
for(const value of [[],[0,1,2,3],[3,2,1,0],[1,1,1,1],Array(1),Array(2),[1,,2],new Uint32Array([2,0,1]),new Float64Array([NaN,2,1]),Object.freeze([2,0,1]),null,undefined,{},'012'])test(value);
const out={status:'PASS',cases,matching_exception_cases:exceptions,input_arrays_unchanged:true,elapsed_ms:performance.now()-start,oracle:'Exact private key function extracted from preserved017 source prefix; no duplicated expected key implementation.',scope:'Plain dense arrays, fallback values/lengths, sparse/frozen arrays and typed-array fallback. Arbitrary getter/proxy/species side effects remain outside owned-solver contract.'};
writeFileSync(new URL('KEY-EQUIVALENCE.json',import.meta.url),JSON.stringify(out,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(out));
