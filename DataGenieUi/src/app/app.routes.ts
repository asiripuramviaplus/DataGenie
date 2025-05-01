import { Routes } from '@angular/router';
import { SearchBoxComponent } from './Components/search-box/search-box.component'
import { DashboardComponent } from './Components/dashboard/dashboard.component';
import { TicketResolverComponent } from './Components/ticket-resolver/ticket-resolver.component';
export const routes: Routes = [
    { path: '', component: SearchBoxComponent }, // Default route
    { path: 'search', component: SearchBoxComponent },
    { path: 'dashboard', component:  DashboardComponent},
    { path: 'ticket-resolver', component: TicketResolverComponent},

];
