import catalog from './catalog.mjs';
import {createPriceService} from './price-service.mjs';
let handler;
export default {fetch(request,env,ctx){handler??=createPriceService({catalog,cache:caches.default});return handler(request,env,ctx);}};
