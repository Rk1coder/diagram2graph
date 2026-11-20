import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {JSDOM} from 'jsdom';

const dom = new JSDOM();
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const {default: mermaid} = await import('mermaid');

// Parse source only; this script does not render or execute interactions.
mermaid.initialize({startOnLoad: false, securityLevel: 'strict'});
const files = process.argv.slice(2);
if (!files.length) {
  for (const directory of ['examples', 'evaluation/images', 'docs/images', 'tests/fixtures']) {
    if (fs.existsSync(directory)) {
      files.push(...fs.readdirSync(directory).filter(name => name.endsWith('.mmd')).map(name => path.join(directory, name)));
    }
  }
}
if (!files.length) throw new Error('No Mermaid exports found.');
for (const file of files) await mermaid.parse(fs.readFileSync(file, 'utf8'));
const graph = {nodes: [{id:'end',label:'%%{ datum }%%',kind:'process'}],edges:[]};
const generated = execFileSync(process.env.PYTHON || 'python3', ['-c', 'import json,sys;from diagram2graph.graph import to_mermaid;print(to_mermaid(json.loads(sys.argv[1])))', JSON.stringify(graph)], {encoding:'utf8',timeout:15000});
await mermaid.parse(generated);
console.log(`Parsed ${files.length} Mermaid exports and one dynamically generated directive-label regression with Mermaid 12.3.0.`);
