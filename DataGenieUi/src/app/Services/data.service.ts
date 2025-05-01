import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { ApiResponse } from 'app/Components/search-box/search-box.component';
import { Observable } from 'rxjs';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root',
})
export class DataService {
  constructor(private http: HttpClient) {}

  fetchResults(
    offset: number,
    generatedSql: string,
    pageSize: number
  ): Observable<any> {
    const requestBody = { sql_query: generatedSql };
    return this.http.post<any>(
      `${environment.apiUrl}/execute-sql-paginated?offset=${offset}&fetch=${pageSize}`,
      requestBody
    );
  }

  // SQL Generation & Execution //

  generateAndExecuteSql(query: string): Observable<ApiResponse> {
    return this.http.post<ApiResponse>(
      `${environment.apiUrl}/generate-and-execute-sql`,
      { query: query },
      { headers: { 'Content-Type': 'application/json' } }
    );
  }

  //Error Logs//

  getAllErrors(): Observable<any> {
    return this.http.get<any>(`${environment.apiUrl}/get-all-errors`);
  }

  //Ticket Management//

  fetchTickets(): Observable<any> {
    return this.http.get<any>(`${environment.apiUrl}/fetch-ticket-details`);
  }

  proceedAction(payload: any): Observable<any> {
    return this.http.post(
      `${environment.apiUrl}/update-ticket-status`,
      payload
    );
  }

  sendUserMessage(userInput: string): Observable<any> {
    return this.http.get<any>(
      `${environment.apiUrl}/get-ticket-status?ticket_number=${userInput}`
    );
  }

  //DataGenie Metrics//
  getDashboardData(): Observable<any> {
    return this.http.get<any>(`${environment.apiUrl}/getdashboarddata`);
  }
}
