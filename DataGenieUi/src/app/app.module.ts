import { NgModule, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule, NoopAnimationsModule } from '@angular/platform-browser/animations';
import { AppComponent } from './app.component';
import { DashboardComponent } from './Components/dashboard/dashboard.component';
import { SearchBoxComponent } from './Components/search-box/search-box.component';
import { TicketResolverComponent } from './Components/ticket-resolver/ticket-resolver.component';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { NgxChartsModule } from '@swimlane/ngx-charts';
import { HttpClientModule } from '@angular/common/http'; // Import HttpClientModule


@NgModule({
  imports: [
    BrowserModule,
    NoopAnimationsModule, // Disable animations
    BrowserAnimationsModule,
    RouterModule,
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonToggleModule,
    NgxChartsModule
  ],
  providers: [],
  bootstrap: [],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class AppModule { }
