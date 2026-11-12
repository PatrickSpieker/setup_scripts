// Run with a Playwright installation available through NODE_PATH. No production services.
const { chromium } = require('playwright');
const { execFileSync, spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const out = fs.mkdtempSync(path.join(os.tmpdir(), 'ui-flow-browser-'));
const run = path.join(out, 'run');
const python = process.env.PYTHON || 'python3';
const port = 18768;
const server = spawn(python, [path.join(__dirname, 'fixture_server.py'), '--port', String(port)]);
let browser;
function cli(...args) { return execFileSync(python, [path.join(root, 'scripts/report.py'), '--run', run, ...args], {encoding:'utf8'}); }
function record(kind, data) { const file = path.join(out, 'input.json'); fs.writeFileSync(file, JSON.stringify(data)); return cli(kind, '--input', file); }
function action(id, from, label, effect='read-only') { record('action', {id, from, label, effect, provenance:'ui: controlled fixture'}); }
async function capture(page, id, title, key=id) {
  const screenshot = path.join(out, id + '.png');
  await page.screenshot({path:screenshot});
  record('state', {id, title, key, screenshot, evidence:'Observed by Playwright navigation in fixture', url:page.url()});
}
async function step(page, id, from, to, label, operation, title) {
  action(id, from, label);
  assert.match(cli('begin', id), /READY/);
  await operation();
  if (title) await capture(page, to, title);
  cli('resolve', id, '--to', to, '--evidence', 'Visible destination verified');
}
(async () => {
  for (let i=0; i<50; i++) { try { await fetch(`http://127.0.0.1:${port}/profile`); break; } catch { await new Promise(r=>setTimeout(r,100)); } }
  browser = await chromium.launch(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {});
  const context = await browser.newContext({viewport:{width:1000,height:760}});
  const page = await context.newPage();
  cli('init','--title','Fixture UI report','--app','Synthetic workspace','--platform','web','--role','test member','--device','1000x760','--theme','light','--build','fixture-v1');
  await page.goto(`http://127.0.0.1:${port}`);
  await capture(page, 'home', 'Workspace');
  await step(page,'menu','home','menu-open','Click Menu',()=>page.getByRole('button',{name:'Menu',exact:true}).click(),'Menu open');
  action('settings','menu-open','Click Settings'); cli('block','settings','--reason','outside requested workflow','--explanation','Settings are outside this verification journey');
  await step(page,'close-menu','menu-open','home','Click Close menu',()=>page.getByRole('button',{name:'Close menu'}).click());
  await step(page,'edit','home','modal','Click Edit profile',()=>page.getByRole('button',{name:'Edit profile',exact:true}).click(),'Edit profile modal');
  await step(page,'invalid','modal','error','Click Save with an empty name',()=>page.getByRole('button',{name:'Save',exact:true}).click(),'Name required');
  record('change',{id:'name',description:'Synthetic profile name',original:'Test Member',expected:'Flow Test',status:'pending',explanation:'Restore after capture'});
  action('save','error','Enter Flow Test and click Save','test-account'); assert.match(cli('begin','save'),/READY/);
  await page.getByRole('textbox',{name:'Name'}).fill('Flow Test'); await page.getByRole('button',{name:'Save',exact:true}).click(); await page.getByText('Flow Test',{exact:true}).waitFor();
  await capture(page,'saved','Profile saved'); cli('resolve','save','--to','saved','--evidence','Backend and UI name updated');
  assert.equal((await (await fetch(`http://127.0.0.1:${port}/profile`)).json()).name,'Flow Test');
  await step(page,'load','saved','loading','Click Load records',()=>page.getByRole('button',{name:'Load records'}).click(),'Loading records');
  await step(page,'loaded','loading','records','Wait for records',()=>page.getByRole('button',{name:'Record 1',exact:true}).waitFor(),'Records ready');
  await step(page,'record1','records','record','Click Record 1',()=>page.getByRole('button',{name:'Record 1',exact:true}).click(),'Record details');
  await step(page,'back1','record','records','Click Back',()=>page.getByRole('button',{name:'Back',exact:true}).click());
  await step(page,'record2','records','record','Click Record 2 (equivalent behavior)',()=>page.getByRole('button',{name:'Record 2',exact:true}).click());
  await page.getByRole('button',{name:'Back',exact:true}).click();
  await step(page,'archived','records','archived-record','Click Archived record',()=>page.getByRole('button',{name:'Archived record',exact:true}).click(),'Record details (archived)');
  action('external','saved','Send to external recipient','external'); assert.match(cli('begin','external'),/BLOCKED/);
  assert.equal((await (await fetch(`http://127.0.0.1:${port}/profile`)).json()).external_count,0);
  action('admin','home','Open admin-only tools'); cli('block','admin','--reason','unreachable','--explanation','Source-discovered admin branch is unavailable to this role');
  action('pending','home','A long action label '.repeat(20));
  cli('finish','--status','stopped','--explanation','Controlled verification stops with a pending branch');
  const profile=await (await fetch(`http://127.0.0.1:${port}/profile`)).json();
  assert.equal(profile.name,'Flow Test');
  await fetch(`http://127.0.0.1:${port}/profile`,{method:'POST',body:JSON.stringify({name:'Test Member'})});
  record('change',{id:'name',description:'Synthetic profile name',status:'restored',explanation:'Compared expected value; restored original'});
  record('change',{id:'conflict',description:'Simulated concurrent profile edit',status:'left-behind',explanation:'Current value differs; preserved unrelated edit'});
  const checkpoint=JSON.parse(fs.readFileSync(path.join(run,'graph.json')));
  assert.equal(checkpoint.states.length,9);
  assert.equal(checkpoint.actions.find(a=>a.id==='record2').to,'record');
  await context.setOffline(true);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('file://' + path.join(run,'report.html'));
  await page.waitForFunction(()=>document.querySelectorAll('.edge').length>0);
  assert.equal(await page.locator('.node').count(),13);
  assert.equal(await page.locator('.shot img').evaluateAll(imgs=>imgs.filter(i=>!i.complete||!i.naturalWidth).length),0);
  const overlaps=await page.locator('.node').evaluateAll(nodes=>{const r=nodes.map(n=>n.getBoundingClientRect());let overlaps=0;for(let i=0;i<r.length;i++)for(let j=i+1;j<r.length;j++)if(r[i].left<r[j].right&&r[i].right>r[j].left&&r[i].top<r[j].bottom&&r[i].bottom>r[j].top)overlaps++;return overlaps});
  assert.equal(overlaps,0);
  const labelProblems=await page.locator('.edge-label').evaluateAll(labels=>{
    const nodes=[...document.querySelectorAll('.node')].map(n=>n.getBoundingClientRect());
    const boxes=labels.map(n=>n.getBoundingClientRect());
    const intersects=(a,b)=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top;
    return labels.filter((label,i)=>label.scrollHeight>label.clientHeight+1||nodes.some(n=>intersects(boxes[i],n))||boxes.some((b,j)=>j>i&&intersects(boxes[i],b))).length;
  });
  assert.equal(labelProblems,0);
  await page.getByRole('searchbox').fill('Edit profile');
  assert.match(await page.locator('#matches').innerText(),/\/2/);
  await page.locator('#search').fill(''); await page.locator('#fit').click();
  await page.locator('.shot').first().click({force:true}); assert.equal(await page.locator('dialog[open]').count(),1); await page.getByRole('button',{name:'Close',exact:true}).click();
  await page.locator('.heading').first().click({force:true}); assert.match(await page.locator('#detail-content').innerText(),/Navigation evidence/); await page.locator('#close-details').click();
  const before=await page.locator('#world').getAttribute('style'); await page.locator('#in').click(); assert.notEqual(await page.locator('#world').getAttribute('style'),before);
  const beforePan=await page.locator('#world').getAttribute('style');await page.mouse.move(20,300);await page.mouse.down();await page.mouse.move(100,350);await page.mouse.up();assert.notEqual(await page.locator('#world').getAttribute('style'),beforePan);
  await page.locator('#coverage').click(); assert.match(await page.locator('#detail-content').innerText(),/preserved unrelated edit/); await page.locator('#close-details').click(); await page.locator('#fit').click();
  await page.screenshot({path:path.join(out,'report-overview.png')});
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({out,states:checkpoint.states.length,actions:checkpoint.actions.length,offline:true,nodeOverlaps:overlaps}));
})().catch(error=>{console.error(error);process.exitCode=1}).finally(async()=>{if(browser)await browser.close();server.kill();});
