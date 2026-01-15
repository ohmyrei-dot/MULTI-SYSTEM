import React, { useState, useEffect } from 'react';
import { Upload, ArrowRight, CheckCircle, AlertCircle, FileSpreadsheet, Calculator } from 'lucide-react';

const PriceComparator = () => {
  const [data, setData] = useState([]);
  const [vendorList, setVendorList] = useState([]);
  const [vendorA, setVendorA] = useState('');
  const [vendorB, setVendorB] = useState('');
  const [fileName, setFileName] = useState('');
  const [quantities, setQuantities] = useState({}); // 수량 상태 관리
  const [isLibLoaded, setIsLibLoaded] = useState(false);

  // XLSX 라이브러리 동적 로드
  useEffect(() => {
    const script = document.createElement('script');
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js";
    script.async = true;
    script.onload = () => setIsLibLoaded(true);
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    }
  }, []);

  // 데이터를 피벗(Pivot)하여 비교하기 쉬운 형태로 변환하는 함수
  const processRawData = (rawData) => {
    const pivoted = {};
    const vendors = new Set();

    rawData.forEach(row => {
      const vendor = row['업체명'] || row['거래처'] || row['매입처'];
      const item = row['품목명'] || row['품명'] || row['상품명'];
      const spec1 = row['규격1'] || row['규격'] || '';
      const spec2 = row['규격2'] || '';
      const price = row['단가'] || row['매입가'] || row['가격'];

      if (!vendor || !item || !price) return;

      vendors.add(vendor);

      const specFull = spec2 ? `${spec1} ${spec2}` : spec1;
      const key = `${item}__${specFull}`;

      if (!pivoted[key]) {
        pivoted[key] = {
          originalKey: key,
          '품목명': item,
          '규격': specFull
        };
      }
      pivoted[key][vendor] = parseFloat(price);
    });

    const processedData = Object.values(pivoted);
    const uniqueVendors = Array.from(vendors);

    // 초기 수량 설정 (기본 1개)
    const initialQuantities = {};
    processedData.forEach(item => {
      initialQuantities[item.originalKey] = 1;
    });

    setData(processedData);
    setVendorList(uniqueVendors);
    setQuantities(initialQuantities);

    if (uniqueVendors.length > 0) setVendorA(uniqueVendors[0]);
    if (uniqueVendors.length > 1) setVendorB(uniqueVendors[1]);
  };

  // 수량 변경 핸들러
  const handleQuantityChange = (key, value) => {
    const newQty = parseInt(value) || 0;
    setQuantities(prev => ({
      ...prev,
      [key]: newQty
    }));
  };

  const handleFileUpload = (e) => {
    if (!isLibLoaded) {
      alert("엑셀 처리 라이브러리가 아직 로딩 중입니다. 잠시만 기다려주세요.");
      return;
    }
    const file = e.target.files[0];
    if (!file) return;

    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (evt) => {
      const bstr = evt.target.result;
      const XLSX = window.XLSX;
      const wb = XLSX.read(bstr, { type: 'binary' });
      const wsname = wb.SheetNames[0];
      const ws = wb.Sheets[wsname];
      const jsonData = XLSX.utils.sheet_to_json(ws);
      if (jsonData.length > 0) processRawData(jsonData);
    };
    reader.readAsBinaryString(file);
  };

  // 총액 계산 (수량 반영)
  const calculateTotal = (vendorName) => {
    return data.reduce((acc, row) => {
      const price = row[vendorName] || 0;
      const qty = quantities[row.originalKey] || 0;
      return acc + (price * qty);
    }, 0);
  };

  const totalA = calculateTotal(vendorA);
  const totalB = calculateTotal(vendorB);
  const totalDiff = totalA - totalB;

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8 font-sans text-slate-800">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* 헤더 섹션 */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
          <h1 className="text-2xl font-bold text-slate-900 mb-2 flex items-center gap-2">
            <Calculator className="w-8 h-8 text-blue-600" />
            최저가 견적 산출기
          </h1>
          <p className="text-slate-500 mb-6">
            엑셀을 업로드하고 <strong>수량</strong>을 입력하면 총 견적을 비교해줍니다.
          </p>

          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center bg-blue-50 p-4 rounded-lg border border-blue-100">
            <div className="flex-1 w-full">
              <label className="block text-sm font-medium text-blue-900 mb-1">
                단가표 엑셀 업로드
              </label>
              <div className="flex gap-2">
                <input 
                  type="file" 
                  accept=".xlsx, .xls" 
                  onChange={handleFileUpload}
                  disabled={!isLibLoaded}
                  className="block w-full text-sm text-slate-500
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-full file:border-0
                    file:text-sm file:font-semibold
                    file:bg-blue-600 file:text-white
                    hover:file:bg-blue-700
                    disabled:opacity-50
                  "
                />
              </div>
              {!isLibLoaded && <p className="text-xs text-slate-400 mt-1">기능 로딩 중...</p>}
            </div>
          </div>
        </div>

        {data.length > 0 && (
          <>
            {/* 업체 선택 및 결과 섹션 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
                <label className="block text-sm font-semibold text-slate-500 mb-2">비교 업체 1 (기준)</label>
                <select 
                  value={vendorA} 
                  onChange={(e) => setVendorA(e.target.value)}
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-lg font-bold"
                >
                  {vendorList.map(v => <option key={`a-${v}`} value={v}>{v}</option>)}
                </select>
                <div className="mt-4 p-4 bg-slate-50 rounded-lg flex justify-between items-center">
                  <span className="text-sm text-slate-500">총 견적 금액</span>
                  <div className="text-2xl font-bold text-slate-800">
                    {totalA.toLocaleString()}원
                  </div>
                </div>
              </div>

              <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
                <label className="block text-sm font-semibold text-slate-500 mb-2">비교 업체 2 (비교)</label>
                <select 
                  value={vendorB} 
                  onChange={(e) => setVendorB(e.target.value)}
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-lg font-bold"
                >
                  {vendorList.map(v => <option key={`b-${v}`} value={v}>{v}</option>)}
                </select>
                <div className="mt-4 p-4 bg-slate-50 rounded-lg flex justify-between items-center">
                  <span className="text-sm text-slate-500">총 견적 금액</span>
                  <div className={`text-2xl font-bold ${totalB < totalA ? 'text-green-600' : 'text-slate-800'}`}>
                    {totalB.toLocaleString()}원
                  </div>
                </div>
              </div>
            </div>

            {/* 총 결과 요약 */}
            <div className={`p-6 rounded-xl text-center border ${totalDiff > 0 ? 'bg-green-50 border-green-200' : totalDiff < 0 ? 'bg-red-50 border-red-200' : 'bg-slate-50 border-slate-200'}`}>
              <h3 className="text-lg font-medium text-slate-600 mb-1">견적 분석 결과</h3>
              <div className="text-3xl font-bold flex items-center justify-center gap-2">
                {totalDiff > 0 ? (
                  <>
                    <CheckCircle className="text-green-600" />
                    <span className="text-green-700">
                      {vendorB} 견적이 {totalDiff.toLocaleString()}원 더 저렴합니다!
                    </span>
                  </>
                ) : totalDiff < 0 ? (
                  <>
                    <AlertCircle className="text-red-500" />
                    <span className="text-red-700">
                      {vendorB} 견적이 {Math.abs(totalDiff).toLocaleString()}원 더 비쌉니다.
                    </span>
                  </>
                ) : (
                  <span className="text-slate-600">견적 금액이 동일합니다.</span>
                )}
              </div>
            </div>

            {/* 상세 비교 테이블 */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
                <h2 className="font-bold text-slate-700">품목별 상세 견적서</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-100 text-slate-600 uppercase font-medium">
                    <tr>
                      <th className="px-4 py-3 min-w-[150px]">품목명</th>
                      <th className="px-4 py-3">규격</th>
                      <th className="px-4 py-3 w-24 text-center bg-yellow-50 text-yellow-800 border-x border-yellow-100">수량</th>
                      <th className="px-4 py-3 bg-blue-50 text-blue-800 text-right">{vendorA}<br/><span className="text-xs font-normal">(단가)</span></th>
                      <th className="px-4 py-3 bg-green-50 text-green-800 text-right">{vendorB}<br/><span className="text-xs font-normal">(단가)</span></th>
                      <th className="px-4 py-3 text-right">단가 차이</th>
                      <th className="px-4 py-3 text-right bg-slate-50 border-l border-slate-200">총 차액<br/><span className="text-xs font-normal">(수량×차액)</span></th>
                      <th className="px-4 py-3 text-center">추천</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.map((row, idx) => {
                      const priceA = row[vendorA];
                      const priceB = row[vendorB];
                      const qty = quantities[row.originalKey] || 0;
                      
                      if (priceA === undefined || priceB === undefined) {
                         return (
                          <tr key={idx} className="hover:bg-slate-50 text-slate-400">
                            <td className="px-4 py-3 font-medium">{row['품목명']}</td>
                            <td className="px-4 py-3">{row['규격']}</td>
                            <td className="px-4 py-3 text-center bg-yellow-50/30">
                              <input 
                                type="number" 
                                min="0"
                                value={qty}
                                onChange={(e) => handleQuantityChange(row.originalKey, e.target.value)}
                                className="w-16 p-1 text-center border rounded bg-white"
                              />
                            </td>
                            <td className="px-4 py-3 text-right">-</td>
                            <td className="px-4 py-3 text-right">-</td>
                            <td className="px-4 py-3 text-right">-</td>
                            <td className="px-4 py-3 text-right">-</td>
                            <td className="px-4 py-3 text-center text-xs">정보 부족</td>
                          </tr>
                         );
                      }

                      const diff = priceB - priceA;
                      const totalDiffItem = diff * qty;
                      const isCheaper = priceB < priceA;

                      return (
                        <tr key={idx} className="hover:bg-slate-50">
                          <td className="px-4 py-3 font-medium text-slate-900">{row['품목명']}</td>
                          <td className="px-4 py-3 text-slate-500">{row['규격']}</td>
                          <td className="px-4 py-3 text-center bg-yellow-50/30 border-x border-yellow-50">
                            <input 
                              type="number" 
                              min="0"
                              value={qty}
                              onChange={(e) => handleQuantityChange(row.originalKey, e.target.value)}
                              className="w-16 p-1 text-center border border-yellow-200 rounded focus:ring-2 focus:ring-yellow-400 outline-none font-bold text-slate-700"
                            />
                          </td>
                          <td className="px-4 py-3 bg-blue-50/30 text-right font-medium text-slate-600">
                            {priceA.toLocaleString()}
                          </td>
                          <td className={`px-4 py-3 bg-green-50/30 text-right font-medium ${isCheaper ? 'text-green-600 font-bold' : 'text-slate-600'}`}>
                            {priceB.toLocaleString()}
                          </td>
                          <td className={`px-4 py-3 text-right font-bold text-slate-400`}>
                            {diff.toLocaleString()}
                          </td>
                          <td className={`px-4 py-3 text-right font-bold bg-slate-50/50 border-l border-slate-100 ${totalDiffItem < 0 ? 'text-green-600' : totalDiffItem > 0 ? 'text-red-500' : 'text-slate-300'}`}>
                            {totalDiffItem.toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {diff < 0 ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                {vendorB}
                              </span>
                            ) : diff > 0 ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                {vendorA}
                              </span>
                            ) : (
                              <span className="text-slate-400">-</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default PriceComparator;
