export function Icon({ name }: { name: string }) {
  const paths: Record<string, string> = {
    home: "M3 10 12 3l9 7M5 9v12h14V9M9 21v-8h6v8",
    building: "M4 21V6l8-3 8 3v15ZM8 8h1m6 0h1M8 12h1m6 0h1M9 21v-5h6v5",
    map: "m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2ZM9 3v16M15 5v16",
    leaf: "M5 19C0 5 12 2 21 3c0 11-5 18-13 15M4 21 16 9",
    box: "m3 7 9-4 9 4v12l-9 3-9-3ZM3 7l9 4 9-4M12 11v11",
    cart: "M2 3h3l3 13h12l2-9H6M9 21h1m8 0h1",
    chart: "M4 21V12h4v9m4 0V8h4v13m4 0V3M3 8l6-4 5 1 7-4",
    sun: "M8 12a4 4 0 1 0 8 0 4 4 0 0 0-8 0M12 2v2m0 16v2M2 12h2m16 0h2M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2",
    truck: "M2 5h12v12H2ZM14 9h4l4 4v4h-8M5 17a2 2 0 1 0 4 0m7 0a2 2 0 1 0 4 0",
    file: "M5 2h9l5 5v15H5ZM14 2v6h5M8 12h8M8 16h8",
  };
  return <svg className="app-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.leaf} /></svg>;
}
