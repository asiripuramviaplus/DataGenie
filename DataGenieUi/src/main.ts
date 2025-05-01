import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { provideRouter } from '@angular/router';
import { routes } from './app/app.routes';
import { HttpClientModule, provideHttpClient } from '@angular/common/http';
import { provideNoopAnimations } from '@angular/platform-browser/animations';

bootstrapApplication(AppComponent, {
    providers: [
        provideRouter(routes),
        HttpClientModule,
        provideHttpClient(),
        provideNoopAnimations()
    ]
}).catch(err => console.error(err));