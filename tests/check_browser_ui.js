const fs=require("fs"),vm=require("vm"),assert=require("assert"),parser=require("@babel/parser");
const file=fs.readFileSync("web/cinematic-library.js","utf8");
parser.parse(file,{sourceType:"module"});
const catalog=JSON.parse(fs.readFileSync("web/catalog.json","utf8"));
const storage=new Map(), notifications=[], callbacks={};
const ctx={
  URL, console, Math, Date,
  localStorage:{
    getItem:(k)=>storage.get(k)??null,
    setItem:(k,v)=>storage.set(k,String(v)),
  },
  window:{
    prompt:(s,defaultName)=>"From Image",
    alert:(msg)=>notifications.push(msg),
  },
  fetch:async()=>({ok:true,json:async()=>catalog}),
  app:{registerExtension:(e)=>callbacks.extension=e},
};
vm.createContext(ctx);
const source=file.replace('import { app } from "/scripts/app.js";','')
                 .replaceAll('import.meta.url','"http://127.0.0.1:8188/extensions/look/library.js"');
vm.runInContext(source+";this.TEST={selected,loadSelection,changeComponent,readVisionRecipe,getPresets};",ctx);
const names=["preset","camera","lens","optical","grade","texture","enabled","vision_preset"];
const node={comfyClass:"SFT_CinematicLookComposer",
  widgets:names.map(name=>({name,value:name==="preset"?"Custom Mix":name==="enabled"?true:name==="vision_preset"?"":"None"})),
  setDirtyCanvas:()=>{},
};
const get=(name)=>node.widgets.find(w=>w.name===name)?.value;
const recipe={source:"vision",selection:{camera:"alexa35",lens:"panac",optical:"glow",grade:"cyan",texture:"fine"},
 descriptions:{camera:"Soft shoulder",lens:"Oval bokeh",optical:"Bloom",grade:"Cool grade",texture:"Fine grain"}};
ctx.TEST.loadSelection(node,catalog,recipe.selection,recipe.descriptions);
assert.equal(get("camera"),"ARRI ALEXA 35");
assert.equal(JSON.parse(get("vision_preset")).descriptions.lens,"Oval bokeh");
ctx.TEST.changeComponent(node,catalog,"lens","Cooke Panchro Classic");
const altered=JSON.parse(get("vision_preset"));
assert.equal(altered.selection.lens,"panchro");
assert.equal(altered.descriptions.lens,"");
assert.equal(altered.descriptions.grade,"Cool grade");
ctx.TEST.loadSelection(node,catalog,catalog.system_presets[0].selection);
assert.equal(get("vision_preset"),"");
let action;
const analyzerNode={comfyClass:"SFT_CinematicVisionAnalyzer",
 addWidget:(kind,label,value,callback)=>{if(label==="Save Vision Preset")action=callback;},
};
callbacks.extension.nodeCreated(analyzerNode);
analyzerNode.onExecuted({cinematic_preset:[JSON.stringify(recipe)]});
(async()=> {
 await action();
 const saved=ctx.TEST.getPresets();
 assert.equal(saved.length,1);
 assert.equal(saved[0].name,"From Image");
 assert.equal(saved[0].descriptions.texture,"Fine grain");
 console.log("JS syntax + category replacement + rich preset save/load smoke tests: OK");
})().catch(e=>{console.error(e);process.exitCode=1});
