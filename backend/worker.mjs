import catalog from './catalog.mjs';
import {createPriceService} from './price-service.mjs';
import {createFinderService} from './finder-service.mjs';
let prices,finder;
export default {fetch(request,env,ctx){
 if(new URL(request.url).pathname.startsWith('/v1/finder/')){finder??=createFinderService({database:env.WATCHES_D1});return finder(request,env,ctx);}
 prices??=createPriceService({catalog,cache:caches.default});return prices(request,env,ctx);
}};
