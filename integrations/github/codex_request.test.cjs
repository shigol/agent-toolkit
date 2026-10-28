const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const {briefPath, parse, dispatch} = require('./codex_request.cjs');
function fixture() {
 const root = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-request-'));
 fs.mkdirSync(path.join(root, 'docs')); fs.writeFileSync(path.join(root, 'docs/brief.md'), 'Read only.');
 return root;
}
test('only a single anchored command is accepted', () => {
 assert.equal(parse('/codex-run docs/brief.md'), 'docs/brief.md');
 for (const s of ['/codex-run docs/brief.md\nother', 'hello /codex-run docs/brief.md', '/codex-run docs/brief.md --ref evil']) assert.throws(() => parse(s));
});
test('brief paths reject traversal, missing files and symlink escapes', () => {
 const root=fixture();
 try {
  assert.equal(briefPath('docs/brief.md',root),'docs/brief.md');
  for(const p of ['docs/../brief.md','/tmp/brief.md','docs//brief.md','docs/no.md','docs/brief.txt']) assert.throws(()=>briefPath(p,root));
  fs.symlinkSync('/etc/hosts',path.join(root,'docs/out.md')); assert.throws(()=>briefPath('docs/out.md',root));
  fs.writeFileSync(path.join(root,'docs/big.md'),'x'.repeat(65537)); assert.throws(()=>briefPath('docs/big.md',root));
 } finally {fs.rmSync(root,{recursive:true,force:true});}
});
function client(permission='read') {
 const calls=[];
 const github={rest:{repos:{getCollaboratorPermissionLevel:async()=>({data:{permission}})},actions:{createWorkflowDispatch:async v=>calls.push(v)},issues:{createComment:async v=>calls.push(v)}}};
 const context={repo:{owner:'shigol',repo:'example'},payload:{repository:{default_branch:'main'},comment:{id:42,body:'/codex-run docs/brief.md',user:{login:'shigol'}},issue:{number:1,pull_request:{head:{ref:'untrusted'}}}}};
 return {github,context,calls};
}
test('owner dispatch always uses default branch and correlates completion',async()=>{
 const root=fixture(), c=client();
 try {await dispatch({...c,root}); assert.equal(c.calls[0].ref,'main'); assert.equal(c.calls[0].workflow_id,'codex-task.yml'); assert.equal(c.calls[0].inputs.request_id,'42');} finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('writers allowed; readers denied before reading a brief or dispatching',async()=>{
 const root=fixture();
 try {
  const denied=client();denied.context.payload.comment.user.login='reader';await assert.rejects(dispatch({...denied,root}));assert.equal(denied.calls.length,0);
  const writer=client('write');writer.context.payload.comment.user.login='claude-writer';await dispatch({...writer,root});assert.equal(writer.calls.length,2);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('acceptance modes are an explicit whitelist and cannot select a ref or inline prompt',async()=>{
 const root=fixture();
 try {
  for(const mode of ['native','global','value-smoke','value','replay-smoke']) {
   const c=client();c.context.payload.comment.body='/codex-run docs/brief.md '+mode;
   await dispatch({...c,root});assert.equal(c.calls[0].inputs.mode,mode);assert.equal(c.calls[0].ref,'main');
  }
  for(const body of ['/codex-run docs/brief.md unknown','/codex-run docs/brief.md value --ref attacker','/codex-run docs/brief.md value;evil']) assert.throws(()=>parse(body));
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
