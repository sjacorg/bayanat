# Data Export

Export items from the database to multiple formats, optionally including related media files.

## Enabling

The export tool must be enabled in the environment configuration. See [Configuration](/deployment/configuration) for details.

## Permissions

- All administrators can make export requests
- Individual users can be granted the `Can Request Exports` permission
- Only administrators can approve or reject export requests

## Output Formats

| Format | Actor | Bulletin | Incident |
| --- | --- | --- | --- |
| PDF | Yes | Yes | Yes |
| JSON | Yes | Yes | Yes |
| CSV | Yes | Yes | No |
| Media | Yes | Yes | No |

PDF exports include all item fields and metadata in a formatted document. JSON exports contain the full structured data. CSV exports provide tabular data suitable for spreadsheet analysis. Media exports bundle all attached files.

## Workflow

```mermaid
%%{ init: { 'theme': 'base', 'themeVariables': { 'primaryColor': '#171717', 'lineColor': '#525252', 'primaryTextColor': '#fafafa', 'secondaryColor': '#262626', 'tertiaryColor': '#1a1a1a', 'primaryBorderColor': '#404040', 'fontFamily': 'system-ui, -apple-system, sans-serif', 'fontSize': '13px' }, 'flowchart': { 'curve': 'basis', 'htmlLabels': false} } }%%
graph TB

  subgraph 0 [Permission]
    A[Admin]
    B[Users with Can Request Exports permission]
  end

  A & B --> C

  subgraph 1 [Request]
    C(Select items to export)
    C --> D(Choose output format and media option)
    D --> E(Submit export request)
  end

  E --> G(Sent to Export dashboard for admin approval)
  G --> H
  G --> I

  subgraph 2 [Approval]
    I{Approved}
    H{Rejected}
    I -.-> L[Admin can reject after approval]
    L -.-> H
  end

  I ----> J(Export generated)
  J --> K(Download link ready)
  K --> T

  subgraph 3 [Download]
    T(User views own requests in export dashboard)
    T --> V(Download available before expiry)
    V -..-> X(Admin can change expiry time)
    X -..-> V
  end

  V ----> M(Request expires)
  M --> Y

  subgraph 4 [Expiry]
    Y((Expired))
    Y --> Z(Download no longer available)
    Z --> ZZ(Export files deleted)
  end

style A fill:#0070f3,stroke:#0060df,color:#fff
style B fill:#0070f3,stroke:#0060df,color:#fff
style C fill:#333,stroke:#444,color:#aaa
style D fill:#333,stroke:#444,color:#aaa
style E fill:#333,stroke:#444,color:#aaa
style G fill:#333,stroke:#444,color:#aaa
style H fill:#e00,stroke:#c00,color:#fff
style I fill:#50e3c2,stroke:#3cc7a8,color:#111
style J fill:#50e3c2,stroke:#3cc7a8,color:#111
style K fill:#50e3c2,stroke:#3cc7a8,color:#111
style L fill:#333,stroke:#444,color:#aaa
style M fill:#333,stroke:#444,color:#aaa
style T fill:#7928ca,stroke:#6622aa,color:#fff
style V fill:#7928ca,stroke:#6622aa,color:#fff
style X fill:#333,stroke:#444,color:#aaa
style Y fill:#111,stroke:#333,color:#fff
style Z fill:#111,stroke:#333,color:#fff
style ZZ fill:#111,stroke:#333,color:#fff
```

1. Select items from the data table
2. Choose the export format and whether to include media
3. Submit the export request
4. An administrator reviews and approves or rejects the request
5. Once approved, the export file is available for download
6. Exports have an expiry time, after which they can no longer be downloaded and files are deleted

Administrators can adjust the expiry time or expire an export immediately if needed.

## Security

Export requests go through an approval workflow to prevent unauthorized data extraction. All export activity is logged in the [Activity Monitor](/guide/activity).

::: tip
The Data Export Tool was made possible by funding from the [International Coalition of Sites of Conscience](https://www.sitesofconscience.org/).
:::
