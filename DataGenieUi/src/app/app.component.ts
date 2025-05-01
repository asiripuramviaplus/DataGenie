import { Component } from '@angular/core';
import { RouterModule, Router } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterModule, CommonModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'CTRMA Metrics';

  constructor(private router: Router) {
    // Navigate to /search on page load or refresh
    this.router.navigate(['/search']);
  }

  toggleDashboard(event: any) {
    if (event.target.checked) {
      this.router.navigate(['/dashboard']);
    } else {
      this.router.navigate(['/search']);
    }
  }

  navigateToSearchBox(): void {
    this.router.navigate(['/search']);
    console.log('Navigating to search box...');
    // Turn off dashboard mode
    const dashboardToggle = document.querySelector('#dashboardToggle') as HTMLInputElement;
    if (dashboardToggle) {
        dashboardToggle.checked = false;
    }
  }
}
