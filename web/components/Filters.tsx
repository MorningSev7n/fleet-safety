"use client";
import { useRouter } from "next/navigation";
import { nice } from "@/lib/labels";

type Props = {
  drivers: string[];
  types: string[];
  minDate: string;
  maxDate: string;
  value: { driver: string; type: string; from: string; to: string };
};

// Plain GET form: the filters live in the URL, so the server page and exports read the same values.
export default function Filters({ drivers, types, minDate, maxDate, value }: Props) {
  const router = useRouter();
  const submit = (form: HTMLFormElement) => {
    const p = new URLSearchParams();
    for (const [k, v] of new FormData(form)) if (v) p.set(k, String(v));
    router.replace(`?${p}`, { scroll: false });
  };
  return (
    <form className="filters" onChange={(e) => submit(e.currentTarget)} onSubmit={(e) => { e.preventDefault(); submit(e.currentTarget); }}>
      <label>Driver
        <select name="driver" defaultValue={value.driver}>
          <option value="">All drivers</option>
          {drivers.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
      </label>
      <label>Event type
        <select name="type" defaultValue={value.type}>
          <option value="">All events</option>
          {types.map((t) => <option key={t} value={t}>{nice(t)}</option>)}
        </select>
      </label>
      <div className="date-pair wide">
        <label>From<input type="date" name="from" min={minDate} max={maxDate} defaultValue={value.from} /></label>
        <label>To<input type="date" name="to" min={minDate} max={maxDate} defaultValue={value.to} /></label>
      </div>
    </form>
  );
}
