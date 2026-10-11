// Local stand-in for huggingface.co + cdn.jsdelivr.net (CORS enabled, streamed)
const http=require('http'),fs=require('fs'),path=require('path');
const HF='/home/claude/vendor/hfmock/onnx-community/Kokoro-82M-v1.0-ONNX/resolve/main', TF='/home/claude/vendor/tf/package/dist';
let hits=0;
http.createServer((q,r)=>{
  r.setHeader('Access-Control-Allow-Origin','*');
  if(q.url==='/hits'){r.end(String(hits));return;}
  hits++;
  const f=q.url.startsWith('/hf/')?path.join(HF,decodeURIComponent(q.url.slice(4))):q.url.startsWith('/ort/')?path.join(TF,q.url.slice(5)):null;
  if(!f||!fs.existsSync(f)){r.statusCode=404;r.end('nf');return;}
  r.setHeader('Content-Length',fs.statSync(f).size); fs.createReadStream(f).pipe(r);
}).listen(8766,()=>console.log('mirror up'));
